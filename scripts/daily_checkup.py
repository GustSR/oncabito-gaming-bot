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

from src.sentinela.clients.db_client import get_all_active_users, mark_user_inactive
from src.sentinela.integrations.hubsoft.cliente import check_contract_status
from src.sentinela.services.group_service import is_user_in_group, remove_user_from_group, notify_administrators
from src.sentinela.core.logging_config import setup_logging

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

async def run_daily_checkup():
    """
    Executa a verificação diária de todos os usuários ativos.
    """
    logger.info("=== INICIANDO CHECKUP DIÁRIO ===")

    try:
        # Busca todos os usuários ativos
        active_users = get_all_active_users()
        logger.info(f"Encontrados {len(active_users)} usuários ativos no banco")

        removed_count = 0
        verified_count = 0
        removed_users = []  # Lista para armazenar usuários removidos

        for user_data in active_users:
            user_id = user_data['user_id']
            client_name = user_data['client_name']

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

        logger.info(f"=== CHECKUP CONCLUÍDO ===")
        logger.info(f"📊 ESTATÍSTICAS FINAIS:")
        logger.info(f"   • Total de usuários ativos no banco: {len(active_users)}")
        logger.info(f"   • Usuários com acesso mantido: {verified_count}")
        logger.info(f"   • Usuários removidos por contrato inativo: {removed_count}")
        logger.info(f"   • Taxa de manutenção: {verified_count/len(active_users)*100:.1f}%" if active_users else "   • Taxa de manutenção: N/A")

        if removed_count > 0:
            logger.warning(f"⚠️  {removed_count} usuário(s) foram removidos automaticamente do grupo!")

            # Notifica administradores sobre os usuários removidos
            logger.info("📬 Enviando notificações para administradores...")
            notification_success = await notify_administrators(removed_users)

            if notification_success:
                logger.info("✅ Administradores notificados com sucesso!")
            else:
                logger.error("❌ Falha ao notificar administradores")
        else:
            logger.info(f"✅ Todos os usuários mantiveram acesso - nenhuma remoção necessária")

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