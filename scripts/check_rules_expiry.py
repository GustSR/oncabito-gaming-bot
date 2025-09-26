#!/usr/bin/env python3
"""
Script para verificar e remover usuários que não aceitaram regras no prazo.

Executa verificação de usuários que entraram no grupo mas não aceitaram
as regras dentro de 24 horas, removendo-os automaticamente.
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

from src.sentinela.clients.db_client import get_expired_rules_users, mark_user_expired
from src.sentinela.services.group_service import remove_user_from_group, notify_administrators
from src.sentinela.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

async def process_expired_users():
    """
    Processa usuários que expiraram sem aceitar regras.
    """
    logger.info("=== VERIFICANDO USUÁRIOS COM REGRAS EXPIRADAS ===")

    try:
        # Busca usuários expirados
        expired_users = get_expired_rules_users()
        logger.info(f"Encontrados {len(expired_users)} usuários com regras expiradas")

        removed_count = 0
        failed_count = 0

        for user_data in expired_users:
            user_id = user_data['user_id']
            username = user_data['username']

            try:
                logger.info(f"Processando usuário expirado: {username} (ID: {user_id})")

                # Remove do grupo
                removal_success = await remove_user_from_group(
                    user_id,
                    "Não aceitou regras dentro do prazo (24h)"
                )

                if removal_success:
                    # Marca como expirado no banco
                    mark_user_expired(user_id)
                    removed_count += 1
                    logger.warning(f"🚫 Usuário {username} (ID: {user_id}) removido por não aceitar regras")
                else:
                    failed_count += 1
                    logger.error(f"❌ Falha ao remover usuário {username} (ID: {user_id})")

            except Exception as e:
                logger.error(f"❌ Erro ao processar usuário {username} (ID: {user_id}): {e}")
                failed_count += 1

        # Log final
        logger.info(f"=== VERIFICAÇÃO DE REGRAS CONCLUÍDA ===")
        logger.info(f"📊 ESTATÍSTICAS:")
        logger.info(f"   • Usuários expirados encontrados: {len(expired_users)}")
        logger.info(f"   • Usuários removidos com sucesso: {removed_count}")
        logger.info(f"   • Falhas na remoção: {failed_count}")

        # Notifica administradores se houver remoções
        if removed_count > 0:
            logger.info("📬 Notificando administradores sobre remoções por regras...")

            # Prepara dados para notificação
            removed_users_data = []
            for user_data in expired_users[:removed_count]:  # Só os que foram removidos
                removed_users_data.append({
                    'user_id': user_data['user_id'],
                    'client_name': user_data['username'],
                    'cpf': 'N/A',  # Não temos CPF para estes usuários
                })

            # Envia notificação customizada
            await notify_administrators_rules_expiry(removed_users_data)

        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} usuário(s) não puderam ser removidos - verificar manualmente")

    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO durante verificação de regras: {e}")

async def notify_administrators_rules_expiry(removed_users: list) -> bool:
    """
    Notifica administradores sobre usuários removidos por não aceitar regras.

    Args:
        removed_users: Lista de usuários removidos

    Returns:
        bool: True se notificou com sucesso
    """
    try:
        from src.sentinela.services.group_service import get_group_administrators, send_private_message

        # Busca administradores
        administrators = await get_group_administrators()
        if not administrators:
            logger.warning("Nenhum administrador encontrado para notificar")
            return False

        # Monta a mensagem específica para regras
        message = "⚠️ <b>REMOÇÃO AUTOMÁTICA - REGRAS NÃO ACEITAS</b> ⚠️\n\n"
        message += f"📅 <b>Data:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
        message += f"🚫 <b>USUÁRIOS REMOVIDOS:</b> {len(removed_users)}\n"
        message += f"📋 <b>Motivo:</b> Não aceitaram regras em 24 horas\n\n"

        for i, user in enumerate(removed_users, 1):
            message += f"{i}. <b>{user.get('client_name', 'Nome não disponível')}</b>\n"
            message += f"   • ID: {user.get('user_id', 'N/A')}\n"
            message += f"   • Status: Removido por expiração de regras\n\n"

        message += "⚙️ <b>Ação Automática:</b> Sistema Sentinela\n"
        message += "📝 <b>Configuração:</b> 24h para aceitar regras\n\n"
        message += "🔧 <i>Sistema Sentinela - OnCabo</i>"

        # Envia para todos os administradores
        success_count = 0
        for admin in administrators:
            if await send_private_message(admin['user_id'], message):
                success_count += 1

        logger.info(f"Notificações de regras enviadas para {success_count}/{len(administrators)} administradores")
        return success_count > 0

    except Exception as e:
        logger.error(f"Erro ao notificar administradores sobre regras: {e}")
        return False

def main():
    """Função principal do script."""
    setup_logging()
    logger.info(f"Verificação de regras expiradas iniciada em {datetime.now()}")

    # Executa a verificação
    asyncio.run(process_expired_users())

    logger.info("Verificação de regras expiradas finalizada")

if __name__ == "__main__":
    main()