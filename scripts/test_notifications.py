#!/usr/bin/env python3
"""
Script de teste para verificar notificações aos administradores.

Testa a busca de administradores e envio de mensagens privadas.
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

from src.sentinela.services.group_service import get_group_administrators, notify_administrators
from src.sentinela.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

async def test_get_administrators():
    """Testa a busca de administradores do grupo."""
    logger.info("=== TESTE: BUSCAR ADMINISTRADORES ===")

    try:
        administrators = await get_group_administrators()

        if administrators:
            logger.info(f"✅ Encontrados {len(administrators)} administradores:")
            for admin in administrators:
                logger.info(f"   • {admin.get('first_name', 'N/A')} (@{admin.get('username', 'sem_username')}) - ID: {admin['user_id']}")
                logger.info(f"     Status: {admin['status']}")
        else:
            logger.warning("❌ Nenhum administrador encontrado")

        return administrators

    except Exception as e:
        logger.error(f"❌ Erro ao buscar administradores: {e}")
        return []

async def test_notification_system():
    """Testa o sistema de notificações com dados simulados."""
    logger.info("=== TESTE: SISTEMA DE NOTIFICAÇÕES ===")

    # Dados simulados de usuários removidos
    fake_removed_users = [
        {
            'user_id': 123456789,
            'client_name': 'João Silva (TESTE)',
            'cpf': '12345678901'
        },
        {
            'user_id': 987654321,
            'client_name': 'Maria Santos (TESTE)',
            'cpf': '98765432109'
        }
    ]

    logger.info(f"Testando notificação com {len(fake_removed_users)} usuários simulados...")

    try:
        success = await notify_administrators(fake_removed_users)

        if success:
            logger.info("✅ Teste de notificação concluído com sucesso!")
        else:
            logger.error("❌ Falha no teste de notificação")

        return success

    except Exception as e:
        logger.error(f"❌ Erro durante teste de notificação: {e}")
        return False

async def run_tests():
    """Executa todos os testes de notificação."""
    logger.info(f"🧪 INICIANDO TESTES DE NOTIFICAÇÃO - {datetime.now()}")

    # Teste 1: Buscar administradores
    administrators = await test_get_administrators()

    if not administrators:
        logger.error("❌ Não é possível continuar - nenhum administrador encontrado")
        return

    # Teste 2: Sistema de notificações
    print("\n" + "="*50)
    print("⚠️  ATENÇÃO: O próximo teste enviará mensagens REAIS para os administradores!")
    print("As mensagens serão claramente marcadas como TESTE.")
    print("="*50)

    confirm = input("Deseja continuar com o teste de notificação? (s/N): ").lower()

    if confirm == 's':
        await test_notification_system()
    else:
        logger.info("Teste de notificação cancelado pelo usuário")

    logger.info("🏁 TESTES CONCLUÍDOS")

def main():
    """Função principal do script de teste."""
    setup_logging()

    # Executa os testes
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()