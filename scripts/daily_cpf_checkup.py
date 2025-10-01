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
from sentinela.infrastructure.config.container import get_container, shutdown_container
from sentinela.domain.value_objects.identifiers import UserId
from sentinela.domain.entities.cpf_verification import VerificationStatus

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(root_dir / 'logs' / 'daily_cpf_checkup.log')
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
        self.bot = None
        self.group_id = None
        self.admin_ids = []

    async def initialize(self):
        """Inicializa dependências."""
        logger.info("🚀 Inicializando Daily CPF Checkup...")

        # Carrega variáveis de ambiente
        from dotenv import load_dotenv
        load_dotenv()

        self.group_id = int(os.getenv("TELEGRAM_GROUP_ID", "0"))
        token = os.getenv("TELEGRAM_TOKEN")

        if not token or not self.group_id:
            raise ValueError("TELEGRAM_TOKEN e TELEGRAM_GROUP_ID são obrigatórios")

        # Inicializa bot
        self.bot = Bot(token=token)

        # Inicializa container DI
        self.container = await get_container()
        self.user_repo = self.container.get("user_repository")
        self.cpf_verification_repo = self.container.get("cpf_verification_repository")
        self.cpf_use_case = self.container.get("cpf_verification_use_case")

        # Busca administradores do grupo
        self.admin_ids = await self._get_admin_ids()

        logger.info("✅ Checkup inicializado com sucesso!")

    async def _get_admin_ids(self) -> list:
        """Busca IDs dos administradores do grupo."""
        try:
            admins = await self.bot.get_chat_administrators(self.group_id)
            admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
            logger.info(f"📋 Encontrados {len(admin_ids)} administradores")
            return admin_ids
        except Exception as e:
            logger.error(f"Erro ao buscar administradores: {e}")
            return []

    async def run_checkup(self):
        """Executa verificação diária completa."""
        logger.info("=" * 60)
        logger.info("🔍 INICIANDO VERIFICAÇÃO DIÁRIA DE CPF")
        logger.info(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        logger.info("=" * 60)

        try:
            # Fase 1: Processar verificações expiradas
            await self._phase1_process_expired_verifications()

            # Fase 2: Verificar membros do grupo sem CPF
            await self._phase2_check_members_without_cpf()

            # Fase 3: Detectar e resolver duplicatas
            await self._phase3_handle_duplicates()

            # Fase 4: Estatísticas finais
            await self._phase4_final_stats()

            logger.info("=" * 60)
            logger.info("✅ VERIFICAÇÃO DIÁRIA CONCLUÍDA COM SUCESSO")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO durante checkup: {e}", exc_info=True)

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
                if user_id in self.admin_ids:
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
        """Fase 2: Verifica membros do grupo sem CPF cadastrado."""
        logger.info("\n" + "=" * 60)
        logger.info("👥 FASE 2: Verificando Membros sem CPF")
        logger.info("=" * 60)

        try:
            # Busca membros do grupo (limitado a admins via API, mas podemos verificar quem já tem CPF)
            # Para grupos grandes, requer bot admin com permissões especiais

            admins = await self.bot.get_chat_administrators(self.group_id)
            members_checked = 0
            members_without_cpf = 0
            requests_sent = 0

            for admin in admins:
                user_id = admin.user.id

                if admin.user.is_bot:
                    continue

                members_checked += 1
                user_id_vo = UserId(user_id)

                # Verifica se tem CPF no banco
                user = await self.user_repo.find_by_id(user_id_vo)

                if not user or not user.cpf:
                    # Verifica se já tem verificação pendente
                    pending = await self.cpf_verification_repo.find_by_user_id(user_id_vo)

                    if not pending or pending.status != VerificationStatus.PENDING:
                        # Cria nova solicitação de verificação
                        result = await self.cpf_use_case.start_verification(
                            user_id=user_id,
                            username=admin.user.username or admin.user.first_name,
                            user_mention=f"@{admin.user.username}" if admin.user.username else admin.user.first_name,
                            verification_type="auto_checkup",
                            source_action="daily_checkup"
                        )

                        if result.success:
                            # Envia mensagem privada
                            try:
                                await self.bot.send_message(
                                    chat_id=user_id,
                                    text=(
                                        "🔐 **Verificação de Segurança - OnCabo Gaming**\n\n"
                                        "Olá! Detectamos que você ainda não completou sua "
                                        "verificação de CPF no sistema.\n\n"
                                        "⏰ **Você tem 24 horas** para completar a verificação\n"
                                        "🔒 **Sem verificação:** Remoção automática do grupo\n\n"
                                        "📱 **Para verificar:**\n"
                                        "Use o comando /verificar_cpf aqui no privado\n\n"
                                        "⚠️ **Importante:** Esta é uma medida de segurança para "
                                        "proteger todos os membros do grupo."
                                    ),
                                    parse_mode='Markdown'
                                )
                                requests_sent += 1
                                logger.info(f"📤 Solicitação enviada para {user_id}")
                            except Exception as dm_error:
                                logger.warning(f"Não foi possível enviar DM para {user_id}: {dm_error}")

                        members_without_cpf += 1

            logger.info(f"👥 Membros verificados: {members_checked}")
            logger.info(f"❌ Sem CPF: {members_without_cpf}")
            logger.info(f"📤 Solicitações enviadas: {requests_sent}")

        except Exception as e:
            logger.error(f"Erro na Fase 2: {e}", exc_info=True)

    async def _phase3_handle_duplicates(self):
        """Fase 3: Detecta e reporta CPFs duplicados."""
        logger.info("\n" + "=" * 60)
        logger.info("🔍 FASE 3: Verificando CPFs Duplicados")
        logger.info("=" * 60)

        try:
            duplicate_service = self.container.get("duplicate_cpf_service")

            # Obtém estatísticas de duplicatas
            stats = await duplicate_service.get_duplicate_statistics(days=30)

            duplicate_count = stats.get('duplicate_cpfs', 0)
            logger.info(f"🔍 CPFs únicos: {stats.get('unique_cpfs', 0)}")
            logger.info(f"⚠️ CPFs duplicados: {duplicate_count}")
            logger.info(f"📊 Taxa de duplicação: {stats.get('duplicate_rate', 0):.2f}%")

            if duplicate_count > 0:
                most_duplicated = stats.get('most_duplicated')
                if most_duplicated:
                    logger.warning(
                        f"🚨 CPF mais duplicado: "
                        f"{most_duplicated['duplicate_count']} contas - "
                        f"IDs: {most_duplicated['user_ids']}"
                    )

        except Exception as e:
            logger.error(f"Erro na Fase 3: {e}", exc_info=True)

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

    async def cleanup(self):
        """Limpeza de recursos."""
        if self.container:
            await shutdown_container()
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
