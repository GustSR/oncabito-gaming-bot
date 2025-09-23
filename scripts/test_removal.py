#!/usr/bin/env python3
"""
Script de teste para funcionalidade de remoção automática de usuários.

Este script permite testar a remoção de usuários do grupo sem executar
o checkup completo, útil para desenvolvimento e debugging.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Adiciona o diretório src ao path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sentinela.services.group_service import is_user_in_group, remove_user_from_group, get_group_info
from sentinela.clients.db_client import get_all_active_users, get_user_data
from sentinela.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

async def test_group_connection():
    """Testa conexão com o grupo Telegram."""
    logger.info("=== TESTE DE CONEXÃO COM GRUPO ===")

    try:
        group_info = await get_group_info()
        if group_info:
            logger.info(f"✅ Conexão bem-sucedida!")
            logger.info(f"   • Nome: {group_info.get('title', 'N/A')}")
            logger.info(f"   • Tipo: {group_info.get('type', 'N/A')}")
            logger.info(f"   • Membros: {group_info.get('member_count', 'N/A')}")
            return True
        else:
            logger.error("❌ Falha na conexão com o grupo")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {e}")
        return False

async def test_user_in_group(user_id: int):
    """Testa se um usuário específico está no grupo."""
    logger.info(f"=== TESTE DE VERIFICAÇÃO DE MEMBRO ===")
    logger.info(f"Testando usuário ID: {user_id}")

    try:
        is_member = await is_user_in_group(user_id)
        if is_member:
            logger.info(f"✅ Usuário {user_id} está no grupo")
        else:
            logger.info(f"❌ Usuário {user_id} NÃO está no grupo")
        return is_member
    except Exception as e:
        logger.error(f"❌ Erro ao verificar membro: {e}")
        return False

async def test_user_removal(user_id: int, dry_run: bool = True):
    """Testa remoção de usuário (modo dry-run por padrão)."""
    logger.info(f"=== TESTE DE REMOÇÃO DE USUÁRIO ===")
    logger.info(f"Usuário ID: {user_id}")
    logger.info(f"Modo dry-run: {'Sim' if dry_run else 'NÃO - REMOÇÃO REAL'}")

    if dry_run:
        logger.warning("⚠️  MODO DRY-RUN - Nenhuma remoção será executada")
        logger.info("   Para executar remoção real, use: --real")
        return True

    try:
        # Verifica se está no grupo primeiro
        is_member = await is_user_in_group(user_id)
        if not is_member:
            logger.info(f"ℹ️  Usuário {user_id} não está no grupo, nada para remover")
            return True

        # Executa remoção
        logger.warning(f"🚨 EXECUTANDO REMOÇÃO REAL do usuário {user_id}...")
        success = await remove_user_from_group(user_id, "Teste de remoção")

        if success:
            logger.info(f"✅ Usuário {user_id} removido com sucesso!")
        else:
            logger.error(f"❌ Falha ao remover usuário {user_id}")

        return success

    except Exception as e:
        logger.error(f"❌ Erro durante remoção: {e}")
        return False

async def list_database_users():
    """Lista usuários ativos no banco de dados."""
    logger.info("=== USUÁRIOS NO BANCO DE DADOS ===")

    try:
        users = get_all_active_users()
        logger.info(f"Total de usuários ativos: {len(users)}")

        if users:
            logger.info("Usuários encontrados:")
            for user in users[:5]:  # Mostra apenas os primeiros 5
                logger.info(f"   • ID: {user['user_id']} | Nome: {user.get('client_name', 'N/A')} | CPF: {user.get('cpf', 'N/A')[:3]}***")

            if len(users) > 5:
                logger.info(f"   ... e mais {len(users) - 5} usuários")
        else:
            logger.info("Nenhum usuário ativo encontrado no banco")

        return users

    except Exception as e:
        logger.error(f"❌ Erro ao listar usuários: {e}")
        return []

async def run_tests(user_id: int = None, real_removal: bool = False):
    """Executa todos os testes."""
    logger.info(f"🧪 INICIANDO TESTES DE REMOÇÃO - {datetime.now()}")

    # Teste 1: Conexão com grupo
    group_ok = await test_group_connection()
    if not group_ok:
        logger.error("❌ Teste de conexão falhou - abortando")
        return

    # Teste 2: Listar usuários do banco
    users = await list_database_users()

    # Teste 3: Verificar usuário específico (se fornecido)
    if user_id:
        await test_user_in_group(user_id)
        await test_user_removal(user_id, dry_run=not real_removal)
    elif users:
        # Testa com o primeiro usuário do banco
        test_user = users[0]
        test_user_id = test_user['user_id']
        logger.info(f"🎯 Usando usuário do banco para teste: {test_user_id}")
        await test_user_in_group(test_user_id)
        await test_user_removal(test_user_id, dry_run=not real_removal)
    else:
        logger.warning("⚠️  Nenhum usuário disponível para teste")

    logger.info("🏁 TESTES CONCLUÍDOS")

def main():
    """Função principal do script de teste."""
    setup_logging()

    import argparse
    parser = argparse.ArgumentParser(description='Teste de funcionalidade de remoção')
    parser.add_argument('--user-id', type=int, help='ID específico do usuário para testar')
    parser.add_argument('--real', action='store_true', help='Executar remoção real (não dry-run)')

    args = parser.parse_args()

    if args.real:
        logger.warning("🚨 ATENÇÃO: Modo de remoção real ativado!")
        confirm = input("Tem certeza que deseja executar remoções reais? (digite 'SIM' para confirmar): ")
        if confirm != 'SIM':
            logger.info("Teste cancelado pelo usuário")
            return

    # Executa os testes
    asyncio.run(run_tests(args.user_id, args.real))

if __name__ == "__main__":
    main()