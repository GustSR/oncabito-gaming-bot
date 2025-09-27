#!/usr/bin/env python3
"""
Script para verificação diária dos usuários.

Verifica se todos os usuários ativos no banco ainda possuem serviços ativos
na API HubSoft e remove do grupo aqueles que não possuem mais.

Para usar no futuro:
- Configure este script para rodar diariamente via cron
- Exemplo cron: 0 6 * * * /usr/bin/python3 /path/to/scripts/daily_checkup.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Adiciona o diretório raiz e src ao path para importar módulos
root_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

from src.sentinela.clients.db_client import get_all_active_users, mark_user_inactive, get_user_data
from src.sentinela.integrations.hubsoft.cliente import check_contract_status
from src.sentinela.services.group_service import is_user_in_group, remove_user_from_group, notify_administrators
from src.sentinela.services.cpf_verification_service import CPFVerificationService
from src.sentinela.services.admin_service import admin_service
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID
from src.sentinela.core.logging_config import setup_logging
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

async def verify_user_access(user_data: dict) -> bool:
    """
    Verifica se um usuário ainda deve ter acesso ao grupo.

    Args:
        user_data: Dados do usuário do banco

    Returns:
        bool: True se deve manter acesso, False para remover
    """
    user_id = user_data['user_id']
    cpf = user_data['cpf']
    client_name = user_data['client_name']

    logger.info(f"Verificando acesso para {client_name} (ID: {user_id})")

    try:
        # 1. Verifica se ainda está no grupo
        is_in_group = await is_user_in_group(user_id)
        if not is_in_group:
            logger.info(f"Usuário {user_id} não está mais no grupo")
            return False

        # 2. Verifica se contrato ainda está ativo
        has_active_contract = check_contract_status(cpf)
        if not has_active_contract:
            logger.warning(f"Contrato inativo para {client_name} (ID: {user_id})")

            # Remove do grupo imediatamente
            removal_success = await remove_user_from_group(user_id, "Contrato inativo")
            if removal_success:
                logger.info(f"Usuário {user_id} removido do grupo com sucesso")
            else:
                logger.error(f"Falha ao remover usuário {user_id} do grupo")

            return False

        logger.info(f"Acesso confirmado para {client_name} (ID: {user_id})")
        return True

    except Exception as e:
        logger.error(f"Erro ao verificar usuário {user_id}: {e}")
        return True  # Em caso de erro, mantém o acesso

async def get_group_members() -> list:
    """
    Busca todos os membros do grupo Telegram
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        # Busca administradores
        administrators = await bot.get_chat_administrators(TELEGRAM_GROUP_ID)

        members = []
        for admin in administrators:
            user = admin.user
            if not user.is_bot:  # Ignora bots
                members.append({
                    'user_id': user.id,
                    'username': user.username or f'user_{user.id}',
                    'first_name': user.first_name or '',
                    'status': 'administrator'
                })

        logger.info(f"Encontrados {len(members)} membros/administradores no grupo")
        return members

    except TelegramError as e:
        logger.error(f"Erro do Telegram ao buscar membros do grupo: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar membros do grupo: {e}")
        return []

async def find_members_without_cpf(group_members: list) -> list:
    """
    Identifica membros do grupo que não têm CPF no banco de dados
    """
    members_without_cpf = []

    for member in group_members:
        user_id = member['user_id']
        username = member['username']

        # Verifica se existe no banco com CPF
        user_data = get_user_data(user_id)

        if not user_data or not user_data.get('cpf'):
            # Verifica se não tem verificação pendente
            pending = CPFVerificationService.get_pending_verification(user_id)
            if not pending:
                members_without_cpf.append({
                    'user_id': user_id,
                    'username': username,
                    'first_name': member.get('first_name', ''),
                    'status': member.get('status', 'member'),
                    'reason': 'no_cpf_in_database' if not user_data else 'cpf_field_empty'
                })

    logger.info(f"Encontrados {len(members_without_cpf)} membros sem CPF no banco")
    return members_without_cpf

async def process_members_without_cpf(members_without_cpf: list) -> dict:
    """
    Processa membros sem CPF iniciando processo de re-verificação
    """
    results = {
        'verification_requests_sent': 0,
        'errors': 0,
        'skipped_admins': 0
    }

    for member in members_without_cpf:
        user_id = member['user_id']
        username = member['username']
        status = member['status']

        try:
            # Verifica isenção de administradores usando AdminService
            if await admin_service.should_exempt_from_verification(user_id):
                logger.info(f"Pulando administrador {username} (ID: {user_id})")
                results['skipped_admins'] += 1
                continue

            # Cria verificação pendente
            user_mention = f"@{username}" if username != f'user_{user_id}' else f"[{user_id}]({user_id})"

            success = CPFVerificationService.create_pending_verification(
                user_id=user_id,
                username=username,
                user_mention=user_mention,
                verification_type="auto_checkup",
                source_action="daily_checkup_missing_cpf"
            )

            if success:
                # Envia solicitação de verificação
                await CPFVerificationService.send_cpf_verification_request(
                    user_id, username, "auto_checkup"
                )

                results['verification_requests_sent'] += 1
                logger.info(f"Solicitação de verificação enviada para {username} (ID: {user_id})")
            else:
                results['errors'] += 1
                logger.error(f"Falha ao criar verificação para {username} (ID: {user_id})")

        except Exception as e:
            results['errors'] += 1
            logger.error(f"Erro ao processar membro sem CPF {username} (ID: {user_id}): {e}")

    return results

async def run_daily_checkup():
    """
    Executa a verificação diária completa:
    1. Verifica usuários ativos (funcionalidade original)
    2. Detecta membros do grupo sem CPF e inicia re-verificação
    3. Limpa verificações expiradas
    """
    logger.info("=== INICIANDO CHECKUP DIÁRIO COMPLETO ===")

    try:
        # Busca administradores do grupo para isenção usando o novo serviço
        admin_ids = await admin_service.get_group_administrators()
        logger.info(f"Encontrados {len(admin_ids)} administradores via AdminService. Eles serão isentos da verificação de contrato.")

        # === PARTE 1: VERIFICAÇÃO DE CONTRATOS ATIVOS (ORIGINAL) ===
        logger.info("🔍 FASE 1: Verificando contratos ativos...")

        # Busca todos os usuários ativos
        active_users = get_all_active_users()
        logger.info(f"Encontrados {len(active_users)} usuários ativos no banco")

        removed_count = 0
        verified_count = 0
        skipped_admins_count = 0
        removed_users = []  # Lista para armazenar usuários removidos

        for user_data in active_users:
            user_id = user_data['user_id']
            client_name = user_data['client_name']

            # Verifica isenção para administradores usando o serviço
            if await admin_service.should_exempt_from_verification(user_id):
                logger.info(f"⏭️  Pulando verificação para o administrador {client_name} (ID: {user_id})")
                skipped_admins_count += 1
                verified_count += 1 # Conta como verificado para manter as estatísticas corretas
                continue

            try:
                logger.info(f"📋 Processando usuário {client_name} (ID: {user_id})...")

                # Verifica se ainda deve ter acesso
                should_keep_access = await verify_user_access(user_data)

                if should_keep_access:
                    verified_count += 1
                    logger.info(f"✅ Usuário {client_name} (ID: {user_id}) - Acesso mantido")
                else:
                    # Marca como inativo no banco
                    if mark_user_inactive(user_id):
                        removed_count += 1
                        removed_users.append(user_data)  # Adiciona à lista de removidos
                        logger.warning(f"🚫 Usuário {client_name} (ID: {user_id}) - Marcado como inativo e removido do grupo")
                    else:
                        logger.error(f"❌ Falha ao marcar usuário {client_name} (ID: {user_id}) como inativo no banco")

            except Exception as e:
                logger.error(f"❌ Erro crítico ao processar usuário {client_name} (ID: {user_id}): {e}")
                # Continua com o próximo usuário mesmo em caso de erro

        logger.info(f"✅ FASE 1 CONCLUÍDA - Verificação de contratos")
        logger.info(f"   • Usuários com acesso mantido: {verified_count}")
        logger.info(f"   • Administradores isentos: {skipped_admins_count}")
        logger.info(f"   • Usuários removidos por contrato inativo: {removed_count}")

        # === PARTE 2: DETECÇÃO DE MEMBROS SEM CPF ===
        logger.info("\n🔍 FASE 2: Detectando membros do grupo sem CPF...")

        # Busca membros do grupo
        group_members = await get_group_members()

        if group_members:
            # Identifica membros sem CPF
            members_without_cpf = await find_members_without_cpf(group_members)

            if members_without_cpf:
                logger.warning(f"⚠️ Encontrados {len(members_without_cpf)} membros sem CPF")

                # Processa membros sem CPF
                cpf_results = await process_members_without_cpf(members_without_cpf)

                logger.info(f"📤 Solicitações de verificação enviadas: {cpf_results['verification_requests_sent']}")
                logger.info(f"⏭️ Administradores pulados: {cpf_results['skipped_admins']}")
                if cpf_results['errors'] > 0:
                    logger.warning(f"❌ Erros durante processamento: {cpf_results['errors']}")
            else:
                logger.info("✅ Todos os membros do grupo têm CPF no banco")
        else:
            logger.warning("⚠️ Não foi possível buscar membros do grupo")

        # === PARTE 3: LIMPEZA DE VERIFICAÇÕES EXPIRADAS ===
        logger.info("\n🧹 FASE 3: Limpando verificações expiradas...")
        await CPFVerificationService.cleanup_expired_verifications()

        # === ESTATÍSTICAS FINAIS ===
        verification_stats = CPFVerificationService.get_verification_stats()

        logger.info(f"\n=== CHECKUP DIÁRIO COMPLETO CONCLUÍDO ===")
        logger.info(f"📊 ESTATÍSTICAS FINAIS:")
        logger.info(f"   📋 CONTRATOS ATIVOS:")
        logger.info(f"      • Total de usuários ativos no banco: {len(active_users)}")
        logger.info(f"      • Usuários com acesso mantido: {verified_count}")
        logger.info(f"      • Usuários removidos por contrato inativo: {removed_count}")
        logger.info(f"   🔍 VERIFICAÇÕES CPF:")
        logger.info(f"      • Verificações pendentes: {verification_stats['pending']}")
        logger.info(f"      • Verificações expiradas hoje: {verification_stats['expired']}")
        logger.info(f"      • Sucessos últimas 24h: {verification_stats['last_24h']['successful']}")
        logger.info(f"      • Falhas últimas 24h: {verification_stats['last_24h']['failed']}")

        # Notificações para administradores
        if removed_count > 0:
            logger.warning(f"⚠️  {removed_count} usuário(s) foram removidos automaticamente do grupo por contrato inativo!")

            logger.info("📬 Enviando notificações para administradores...")
            notification_success = await notify_administrators(removed_users)

            if notification_success:
                logger.info("✅ Administradores notificados com sucesso!")
            else:
                logger.error("❌ Falha ao notificar administradores")

        if verification_stats['pending'] > 0:
            logger.info(f"📋 {verification_stats['pending']} verificação(ões) de CPF aguardando resposta")

        logger.info("✅ Checkup diário completo finalizado com sucesso")

    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO durante checkup diário: {e}")
        logger.error(f"   • Verifique conectividade com API HubSoft e Telegram")
        logger.error(f"   • Verifique permissões do bot no grupo")
        logger.error(f"   • Verifique integridade do banco de dados")

def main():
    """Função principal do script."""
    setup_logging()
    logger.info(f"Checkup diário iniciado em {datetime.now()}")

    # Executa o checkup assíncrono
    asyncio.run(run_daily_checkup())

    logger.info("Checkup diário finalizado")

if __name__ == "__main__":
    main()