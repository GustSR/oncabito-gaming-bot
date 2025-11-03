#!/usr/bin/env python3
"""
Script de verificação diária de CPF - Nova Arquitetura.

Verifica:
1. Usuários do grupo sem CPF cadastrado
2. Verific ações de CPF expiradas (24h)
3. Remove usuários que não confirmaram CPF
4. Detecta e resolve CPFs duplicados

Uso:
- Configure via cron para rodar diariamente
- Exemplo: 0 6 * * * python3 /path/to/scripts/daily_cpf_checkup.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from telegram import Bot
from telegram.error import TelegramError

# Imports da nova arquitetura
from sentinela.infrastructure.config.dependency_injection import get_container
from sentinela.domain.value_objects.identifiers import UserId
from sentinela.domain.entities.cpf_verification import VerificationStatus

# Configuração de logging
# Cria diretório de logs se não existir
logs_dir = root_dir / 'logs'
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(logs_dir / 'daily_cpf_checkup.log')
    ]
)
logger = logging.getLogger(__name__)


class DailyCPFCheckup:
    """Gerencia a verificação diária de CPF usando nova arquitetura."""

    def __init__(self):
        self.container = None
        self.user_repo = None
        self.cpf_verification_repo = None
        self.cpf_use_case = None
        self.hubsoft_use_case = None
        self.admin_repo = None
        self.welcome_use_case = None
        self.hubsoft_api = None
        self.bot = None
        self.group_id = None

    async def initialize(self):
        """Inicializa dependências."""
        logger.info("🚀 Inicializando Daily CPF Checkup...")

        # Carrega variáveis de ambiente
        from dotenv import load_dotenv
        load_dotenv()

        # Remove aspas do group_id se existirem (ex: '"-123"' -> -123)
        group_id_str = os.getenv("TELEGRAM_GROUP_ID", "0").strip('"').strip("'")
        self.group_id = int(group_id_str)
        token = os.getenv("TELEGRAM_TOKEN")

        if not token or not self.group_id:
            raise ValueError("TELEGRAM_TOKEN e TELEGRAM_GROUP_ID são obrigatórios")

        # Inicializa bot
        self.bot = Bot(token=token)

        # Inicializa container DI
        self.container = get_container()
        self.user_repo = self.container.get("user_repository")
        self.cpf_verification_repo = self.container.get("cpf_verification_repository")
        self.cpf_use_case = self.container.get("cpf_verification_use_case")
        self.hubsoft_use_case = self.container.get("hubsoft_integration_use_case")
        self.admin_repo = self.container.get("admin_repository")
        self.welcome_use_case = self.container.get("welcome_management_use_case")
        from sentinela.domain.repositories.hubsoft_repository import HubSoftAPIRepository
        self.hubsoft_api = self.container.get(HubSoftAPIRepository)

        logger.info("✅ Checkup inicializado com sucesso!")

    async def run_checkup(self):
        """Executa verificação diária completa."""
        logger.info("=" * 60)
        logger.info("🔍 INICIANDO VERIFICAÇÃO DIÁRIA DE CPF")
        logger.info(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        logger.info("=" * 60)

        try:
            # Fase 0: Sincronizar lista de administradores
            await self._phase_sync_admins()

            # Fase 0.5: Processar conflitos de duplicata expirados (TIMEOUT)
            await self._phase_process_expired_conflicts()

            # Fase 1: Processar verificações de CPF expiradas
            await self._phase1_process_expired_verifications()

            # Fase 3: Processar usuários que não aceitaram as regras
            await self._phase_check_expired_rules()

            # Fase 4: Verificar contratos ativos de membros existentes
            await self._phase_check_active_contracts()

            # Fase 5: Verificar membros do grupo sem CPF
            await self._phase2_check_members_without_cpf()

            # Fase 6: Detectar e resolver duplicatas
            await self._phase3_handle_duplicates()

            # Fase 7: Estatísticas finais
            await self._phase4_final_stats()

            logger.info("=" * 60)
            logger.info("✅ VERIFICAÇÃO DIÁRIA CONCLUÍDA COM SUCESSO")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO durante checkup: {e}", exc_info=True)

    async def _phase_sync_admins(self):
        """Busca os admins atuais do grupo no Telegram e sincroniza com o banco de dados."""
        logger.info("\n" + "=" * 60)
        logger.info("👤 FASE 1: Sincronizando Administradores")
        logger.info("=" * 60)
        
        try:
            logger.info("Buscando administradores do grupo no Telegram...")
            tg_admins = await self.bot.get_chat_administrators(self.group_id)
            
            formatted_admins = []
            for admin in tg_admins:
                if not admin.user.is_bot:
                    formatted_admins.append({
                        "user_id": admin.user.id,
                        "username": admin.user.username,
                        "first_name": admin.user.first_name,
                        "last_name": admin.user.last_name,
                        "status": admin.status,
                    })
            
            logger.info(f"Encontrados {len(formatted_admins)} administradores. Sincronizando com o banco de dados...")
            
            synced_count = await self.admin_repo.sync_from_telegram(formatted_admins)
            
            logger.info(f"✅ Sincronização concluída. {synced_count} administradores ativos no banco.")

        except Exception as e:
            logger.error(f"Erro na fase de sincronização de administradores: {e}", exc_info=True)

    async def _phase_process_expired_conflicts(self):
        """
        Fase 0.5: Processa conflitos de duplicata expirados.

        Quando um usuário não responde no prazo (24h), TODAS as contas
        associadas ao CPF duplicado são removidas do grupo automaticamente.
        Esta é a "penalidade" por não resolver a pendência de segurança.
        """
        logger.info("\n" + "=" * 60)
        logger.info("⏰ FASE 0.5: Processando Conflitos Expirados (TIMEOUT)")
        logger.info("=" * 60)

        try:
            # Busca repository de conflitos
            conflict_repo = self.container.get("duplicate_conflict_repository")

            # Busca conflitos pendentes que expiraram
            expired_conflicts = await conflict_repo.find_expired_pending_conflicts()

            if not expired_conflicts:
                logger.info("✅ Nenhum conflito expirado encontrado")
                return

            logger.warning(f"⚠️ Encontrados {len(expired_conflicts)} conflitos expirados!")

            removed_total = 0
            for conflict in expired_conflicts:
                logger.warning(
                    f"⏱️ Processando conflito expirado {conflict.id.value[:8]}... "
                    f"({len(conflict.user_ids)} usuários envolvidos)"
                )

                # Marca conflito como expirado
                conflict.expire_and_remove_all()

                # Remove TODOS os usuários envolvidos
                for user_id in conflict.user_ids:
                    try:
                        # Remove do grupo do Telegram
                        await self.bot.ban_chat_member(chat_id=self.group_id, user_id=user_id)
                        await self.bot.unban_chat_member(chat_id=self.group_id, user_id=user_id)

                        # Bane usuário no banco
                        await self.user_repo.ban_user(
                            user_id=UserId(user_id),
                            reason=f"Conflito de CPF duplicado expirado sem resolução (ID: {conflict.id.value})"
                        )

                        removed_total += 1
                        logger.warning(f"🚫 Usuário {user_id} removido por timeout de conflito")

                        # Envia mensagem privada explicando
                        try:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=(
                                    "🚫 **Remoção por Conflito de Segurança** 🚫\n\n"
                                    "Você foi removido do grupo OnCabo Gaming devido a um conflito de CPF não resolvido.\n\n"
                                    "**Motivo:** Seu CPF está associado a múltiplas contas do Telegram e você não "
                                    "respondeu à solicitação de resolução dentro do prazo de 24 horas.\n\n"
                                    "**Ação tomada:** Por medida de segurança, todas as contas associadas ao CPF foram removidas.\n\n"
                                    "**Para retornar ao grupo:**\n"
                                    "1. Entre em contato com um administrador\n"
                                    "2. Explique a situação\n"
                                    "3. Realize uma nova verificação com a conta correta\n\n"
                                    "💡 **Importante:** Mantenha apenas UMA conta do Telegram por CPF para evitar problemas de segurança."
                                ),
                                parse_mode='Markdown'
                            )
                        except Exception:
                            pass  # Ignora se não conseguir enviar DM

                    except Exception as e:
                        logger.error(f"Erro ao remover usuário {user_id} do conflito expirado: {e}")

                # Salva conflito atualizado
                await conflict_repo.save(conflict)

                logger.info(
                    f"✅ Conflito {conflict.id.value[:8]}... processado. "
                    f"Status: {conflict.status.value}"
                )

            logger.warning(f"🚫 Total de usuários removidos por timeout: {removed_total}")

        except Exception as e:
            logger.error(f"Erro na fase de processamento de conflitos expirados: {e}", exc_info=True)

    async def _phase1_process_expired_verifications(self):
        """Fase 1: Processa verificações expiradas e remove usuários."""
        logger.info("\n" + "=" * 60)
        logger.info("📋 FASE 1: Processando Verificações Expiradas")
        logger.info("=" * 60)

        # Processa verificações expiradas via use case
        result = await self.cpf_use_case.process_expired_verifications()

        expired_count = result.get('processed_count', 0)
        logger.info(f"⏰ Verificações expiradas processadas: {expired_count}")

        if expired_count > 0:
            # Busca verificações que expiraram hoje
            expired_verifications = await self.cpf_verification_repo.find_by_status(
                VerificationStatus.EXPIRED,
                limit=100
            )

            # Filtra apenas as que expiraram nas últimas 24h
            recently_expired = [
                v for v in expired_verifications
                if v.completed_at and (datetime.now() - v.completed_at) < timedelta(hours=24)
            ]

            removed_count = 0
            for verification in recently_expired:
                user_id = verification.user_id.value

                # Não remove administradores
                if await self.admin_repo.is_administrator(user_id):
                    logger.info(f"⏭️ Pulando administrador: {user_id}")
                    continue

                # Remove do grupo
                try:
                    await self.bot.ban_chat_member(
                        chat_id=self.group_id,
                        user_id=user_id
                    )

                    # Desbanir imediatamente (apenas remove)
                    await self.bot.unban_chat_member(
                        chat_id=self.group_id,
                        user_id=user_id
                    )

                    removed_count += 1
                    logger.warning(f"🚫 Usuário {user_id} removido por não confirmar CPF em 24h")

                    # Tenta enviar mensagem privada explicando
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=(
                                "⚠️ **Remoção por Segurança**\n\n"
                                "Você foi removido do grupo OnCabo Gaming por não completar "
                                "a verificação de CPF dentro do prazo de 24 horas.\n\n"
                                "🔒 **Motivo:** Medida de segurança do grupo\n"
                                "⏰ **Prazo:** 24 horas (expirado)\n\n"
                                "📱 **Para retornar ao grupo:**\n"
                                "1. Complete sua verificação de CPF\n"
                                "2. Entre em contato com um administrador\n\n"
                                "💡 Use /verificar_cpf para iniciar nova verificação"
                            ),
                            parse_mode='Markdown'
                        )
                    except Exception:
                        pass  # Ignora se não conseguir enviar DM

                except TelegramError as e:
                    logger.error(f"Erro ao remover usuário {user_id}: {e}")

            logger.info(f"🚫 Total de usuários removidos: {removed_count}")

        logger.info(f"🧹 Verificações antigas limpas: {result.get('cleanup_count', 0)}")

    async def _phase2_check_members_without_cpf(self):
        """Fase 5: Verifica membros no banco de dados sem CPF e inicia a verificação."""
        logger.info("\n" + "=" * 60)
        logger.info("👥 FASE 5: Verificando Usuários Ativos sem CPF no DB")
        logger.info("=" * 60)

        try:
            users_to_check = await self.user_repo.find_active_users_without_cpf()
            logger.info(f"Encontrados {len(users_to_check)} usuários ativos sem CPF no banco de dados.")

            requests_sent = 0
            for user in users_to_check:
                user_id = user.id.value

                # Ignora administradores
                if await self.admin_repo.is_administrator(user_id):
                    logger.info(f"⏭️ Pulando verificação de CPF para o administrador {user.username} (ID: {user_id})")
                    continue

                # Verifica se já não há uma verificação pendente para este usuário
                pending_verification = await self.cpf_verification_repo.find_pending_by_user(user.id)
                if pending_verification:
                    logger.debug(f"Usuário {user_id} já possui uma verificação pendente. Pulando.")
                    continue

                # Se não há verificação pendente, inicia uma nova
                logger.info(f"Iniciando verificação proativa para o usuário {user.username} (ID: {user_id})")
                result = await self.cpf_use_case.start_verification(
                    user_id=user_id,
                    username=user.username or user.first_name,
                    user_mention=f"@{user.username}" if user.username else user.first_name,
                    verification_type="daily_checkup",
                    source_action="daily_checkup_no_cpf"
                )

                if result.success:
                    # Envia a mensagem direta solicitando o CPF
                    try:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=(
                                "🔐 **Verificação de Segurança - OnCabo Gaming**\n\n"
                                "Olá! Detectamos que você é um membro do nosso grupo, mas ainda não completou sua "
                                "verificação de CPF.\n\n"
                                "Para mantermos a segurança da comunidade, esta verificação é obrigatória.\n\n"
                                "▶️ **Por favor, responda a esta mensagem com o seu CPF (apenas números) para continuar.**\n\n"
                                "⏰ **Prazo:** Você tem 24 horas para completar a verificação, ou seu acesso ao grupo será revogado.\n\n"
                                "🔒 Seus dados são protegidos e usados apenas para esta validação."
                            ),
                            parse_mode='Markdown'
                        )
                        requests_sent += 1
                        logger.info(f"📤 Solicitação de verificação enviada para {user.username} (ID: {user_id})")
                    except Exception as dm_error:
                        logger.warning(f"Não foi possível enviar DM de verificação para {user_id}: {dm_error}")
            
            logger.info(f"✅ Verificação de usuários sem CPF concluída. {requests_sent} solicitações enviadas.")

        except Exception as e:
            logger.error(f"Erro na Fase 5 (Verificar usuários sem CPF): {e}", exc_info=True)

    async def _phase3_handle_duplicates(self):
        """
        Fase 6: Detecção Proativa de Duplicatas.

        Detecta CPFs usados por múltiplas contas, cria conflitos e
        notifica o usuário mais recente para escolher qual conta manter.
        """
        logger.info("\n" + "=" * 60)
        logger.info("🔍 FASE 6: Detecção Proativa de CPFs Duplicados")
        logger.info("=" * 60)

        try:
            duplicate_service = self.container.get("duplicate_cpf_service")
            conflict_repo = self.container.get("duplicate_conflict_repository")

            # 1. Detecta e cria novos conflitos
            logger.info("Iniciando detecção de CPFs duplicados...")
            new_conflicts = await duplicate_service.find_and_flag_new_duplicates(conflict_repo)

            if not new_conflicts:
                logger.info("✅ Nenhum novo conflito de duplicata detectado")
                return

            logger.warning(f"🚨 {len(new_conflicts)} novos conflitos detectados!")

            # 2. Para cada conflito, notifica o usuário com botões de escolha
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            notifications_sent = 0
            for conflict in new_conflicts:
                notified_user_id = conflict.notified_user_id
                conflict_data = conflict.conflict_data
                users_info = conflict_data.get('users', [])

                # Monta mensagem explicativa
                message_text = (
                    "🚨 **ALERTA DE SEGURANÇA - Contas Duplicadas** 🚨\n\n"
                    f"Detectamos que seu CPF está associado a **{len(conflict.user_ids)} contas** diferentes no Telegram:\n\n"
                )

                # Lista as contas envolvidas
                for i, user_info in enumerate(users_info, 1):
                    username = user_info.get('username', 'N/A')
                    first_name = user_info.get('first_name', 'N/A')
                    message_text += f"{i}. @{username} ({first_name})\n"

                message_text += (
                    "\n⚠️ **Por motivos de segurança, apenas UMA conta pode estar associada a cada CPF.**\n\n"
                    "📋 **O que você precisa fazer:**\n"
                    "Por favor, escolha abaixo qual conta você deseja **MANTER ATIVA** no grupo. "
                    "As outras contas serão automaticamente desativadas.\n\n"
                    f"⏰ **Prazo:** Você tem **24 horas** para fazer sua escolha.\n\n"
                    "❗ **IMPORTANTE:** Se não responder no prazo, **TODAS as contas serão removidas** automaticamente."
                )

                # Cria botões inline (um para cada conta)
                keyboard = []
                for user_info in users_info:
                    user_id = user_info['user_id']
                    username = user_info.get('username', 'N/A')
                    first_name = user_info.get('first_name', 'Usuário')

                    button_text = f"✅ Manter @{username} ({first_name})"
                    callback_data = f"resolve_dup:{conflict.id.value}:{user_id}"

                    # Limita callback_data a 64 bytes (limite do Telegram)
                    if len(callback_data) > 64:
                        # Encurta o conflict_id para caber
                        short_conflict_id = conflict.id.value[:8]
                        callback_data = f"resolve:{short_conflict_id}:{user_id}"

                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

                reply_markup = InlineKeyboardMarkup(keyboard)

                # Envia mensagem com botões
                try:
                    await self.bot.send_message(
                        chat_id=notified_user_id,
                        text=message_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )

                    notifications_sent += 1
                    logger.info(
                        f"📤 Notificação enviada para usuário {notified_user_id} "
                        f"(Conflito: {conflict.id.value[:8]}...)"
                    )

                except Exception as dm_error:
                    logger.error(
                        f"❌ Erro ao enviar notificação para usuário {notified_user_id}: {dm_error}"
                    )

            logger.info(f"✅ Notificações enviadas: {notifications_sent}/{len(new_conflicts)}")

            # 3. Mostra estatísticas gerais
            stats = await conflict_repo.get_conflict_statistics(days=30)
            logger.info("\n📊 Estatísticas de Conflitos (últimos 30 dias):")
            logger.info(f"   Total: {stats.get('total', 0)}")
            logger.info(f"   Pendentes: {stats.get('pending', 0)}")
            logger.info(f"   Resolvidos: {stats.get('resolved', 0)}")
            logger.info(f"   Expirados: {stats.get('expired_removed', 0)}")
            logger.info(f"   Taxa de resolução: {stats.get('resolution_rate', '0%')}")

        except Exception as e:
            logger.error(f"Erro na Fase 6 (Detecção de Duplicatas): {e}", exc_info=True)

    async def _phase4_final_stats(self):
        """Fase 4: Estatísticas finais."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 FASE 4: Estatísticas Finais")
        logger.info("=" * 60)

        try:
            # Conta verificações por status
            pending_verifications = await self.cpf_verification_repo.find_by_status(
                VerificationStatus.PENDING,
                limit=1000
            )

            completed_verifications = await self.cpf_verification_repo.find_by_status(
                VerificationStatus.COMPLETED,
                limit=1000
            )

            expired_verifications = await self.cpf_verification_repo.find_by_status(
                VerificationStatus.EXPIRED,
                limit=1000
            )

            logger.info(f"✅ Verificações completas: {len(completed_verifications)}")
            logger.info(f"⏳ Verificações pendentes: {len(pending_verifications)}")
            logger.info(f"⏰ Verificações expiradas: {len(expired_verifications)}")

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")

    async def _phase_check_active_contracts(self):
        """Verifica contratos ativos de usuários com CPF e remove os inativos."""
        logger.info("\n" + "=" * 60)
        logger.info("💼 FASE 4: Verificando Contratos Ativos de Membros")
        logger.info("=" * 60)

        try:
            active_users = await self.user_repo.find_active_users()
            users_with_cpf = [u for u in active_users if u.cpf]
            
            logger.info(f"Encontrados {len(users_with_cpf)} usuários com CPF para verificar.")
            
            removed_count = 0
            for user in users_with_cpf:
                user_id = user.id.value
                
                if await self.admin_repo.is_administrator(user_id):
                    logger.info(f"⏭️  Pulando verificação de contrato para o administrador {user.username} (ID: {user_id})")
                    continue

                logger.info(f"📋 Verificando contrato para {user.username} (ID: {user_id})...")
                
                try:
                    # Chama a API diretamente para uma resposta síncrona
                    api_response = await self.hubsoft_api.verify_client_by_cpf(cpf=user.cpf.value)
                    
                    # A API retorna uma lista de 'clientes' se encontrar um com serviço habilitado
                    is_active = api_response and api_response.get('status') == 'success' and api_response.get('clientes')

                    if not is_active:
                        logger.warning(f"Contrato inativo ou não encontrado para {user.username} (ID: {user_id}). Removendo do grupo.")
                        
                        try:
                            await self.bot.ban_chat_member(chat_id=self.group_id, user_id=user_id)
                            await self.bot.unban_chat_member(chat_id=self.group_id, user_id=user_id)
                            
                            await self.user_repo.ban_user(user_id=user.id, reason="Contrato inativo ou cancelado (checkup diário)")
                            removed_count += 1
                            
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=(
                                    "🚫 Acesso ao grupo OnCabo Gaming removido 🚫\n\n"
                                    "Olá! Em nossa verificação diária, identificamos que seu plano OnCabo Gaming não se encontra mais ativo.\n\n"
                                    "Por esse motivo, seu acesso ao grupo exclusivo foi revogado para manter a comunidade apenas para membros ativos.\n\n"
                                    "Se você acredita que isso é um erro ou gostaria de reativar seu plano para voltar a participar, "
                                    "por favor, entre em contato com nosso suporte comercial."
                                )
                            )
                            logger.info(f"Usuário {user_id} removido do grupo e notificado por DM.")

                        except Exception as e:
                            logger.error(f"Falha ao remover/notificar usuário {user_id}: {e}")
                    else:
                        logger.info(f"✅ Contrato ativo para {user.username} (ID: {user_id}). Acesso mantido.")

                except Exception as api_error:
                    logger.error(f"Erro ao consultar a API HubSoft para o usuário {user_id}: {api_error}")

            logger.info(f"✅ Verificação de contratos concluída. Total de usuários removidos: {removed_count}")

        except Exception as e:
            logger.error(f"Erro na fase de verificação de contratos: {e}", exc_info=True)

    async def _phase_check_expired_rules(self):
        """Verifica e remove usuários que não aceitaram as regras no prazo."""
        logger.info("\n" + "=" * 60)
        logger.info("📜 FASE: Verificando Aceitação de Regras Expiradas")
        logger.info("=" * 60)

        try:
            result = await self.welcome_use_case.check_expired_rules_acceptance()

            if result.success:
                expired_count = result.data.get('expired_count', 0)
                logger.info(f"✅ Verificação de regras concluída. Total de usuários removidos: {expired_count}")
                if expired_count > 0:
                    logger.warning(f"Usuários removidos: {result.data.get('removed_users', [])}")
            else:
                logger.error(f"Ocorreu um erro ao verificar as regras expiradas: {result.message}")

        except Exception as e:
            logger.error(f"Erro na fase de verificação de regras expiradas: {e}", exc_info=True)

    async def cleanup(self):
        """Limpeza de recursos."""
        # Container não precisa de cleanup explícito
        logger.info("🧹 Recursos liberados")


async def main():
    """Função principal."""
    checkup = DailyCPFCheckup()

    try:
        await checkup.initialize()
        await checkup.run_checkup()
    finally:
        await checkup.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
