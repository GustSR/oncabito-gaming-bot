#!/usr/bin/env python3
"""
Script de teste para validar o sistema de descoberta de tópicos.

Testa as funcionalidades de identificação automática de tópicos e
suas configurações.
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

from src.sentinela.services.topics_service import topics_service
from src.sentinela.core.logging_config import setup_logging
from src.sentinela.core.config import TELEGRAM_GROUP_ID, RULES_TOPIC_ID, WELCOME_TOPIC_ID

logger = logging.getLogger(__name__)

async def test_topics_discovery():
    """Testa a descoberta e listagem de tópicos."""
    logger.info("=== TESTE DE DESCOBERTA DE TÓPICOS ===")

    try:
        # Teste 1: Listar tópicos descobertos
        logger.info("📋 Listando tópicos descobertos...")
        topics = await topics_service.get_all_topics()

        if topics:
            logger.info(f"✅ Encontrados {len(topics)} tópicos:")
            for topic in topics:
                logger.info(f"   • {topic['name']} (ID: {topic['id']})")
        else:
            logger.warning("❌ Nenhum tópico descoberto ainda")
            logger.info("💡 Envie mensagens em tópicos do grupo para descobri-los")

        # Teste 2: Formatação de lista
        logger.info("\n📄 Testando formatação de lista...")
        formatted_list = await topics_service.format_topics_list()
        print("\n" + "="*60)
        print("LISTA FORMATADA DE TÓPICOS:")
        print("="*60)
        print(formatted_list.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', ''))
        print("="*60)

        # Teste 3: Sugestões automáticas
        logger.info("\n🔧 Testando sugestões automáticas...")
        suggestions = await topics_service.get_topic_suggestions()

        logger.info("Sugestões encontradas:")
        if suggestions['rules_topic']:
            logger.info(f"   📋 Regras: {suggestions['rules_topic']['name']} (ID: {suggestions['rules_topic']['id']})")
        else:
            logger.info("   📋 Regras: Não encontrado")

        if suggestions['welcome_topic']:
            logger.info(f"   👋 Boas-vindas: {suggestions['welcome_topic']['name']} (ID: {suggestions['welcome_topic']['id']})")
        else:
            logger.info("   👋 Boas-vindas: Não encontrado")

        logger.info(f"   📂 Outros tópicos: {len(suggestions['other_topics'])}")

        # Teste 4: Configuração automática
        logger.info("\n⚙️  Testando configuração automática...")
        auto_config = await topics_service.auto_configure_topics()
        print("\n" + "="*60)
        print("CONFIGURAÇÃO AUTOMÁTICA SUGERIDA:")
        print("="*60)
        print(auto_config.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', ''))
        print("="*60)

        return True

    except Exception as e:
        logger.error(f"❌ Erro durante teste de descoberta: {e}")
        return False

async def test_current_configuration():
    """Testa a configuração atual de tópicos."""
    logger.info("\n=== TESTE DE CONFIGURAÇÃO ATUAL ===")

    try:
        logger.info("📋 Configurações atuais:")
        logger.info(f"   • Grupo ID: {TELEGRAM_GROUP_ID}")
        logger.info(f"   • Tópico Regras: {RULES_TOPIC_ID or 'Não configurado'}")
        logger.info(f"   • Tópico Boas-vindas: {WELCOME_TOPIC_ID or 'Não configurado'}")

        # Verifica se os tópicos configurados existem
        topics = await topics_service.get_all_topics()

        rules_found = False
        welcome_found = False

        if RULES_TOPIC_ID:
            for topic in topics:
                if str(topic['id']) == str(RULES_TOPIC_ID):
                    rules_found = True
                    logger.info(f"✅ Tópico Regras encontrado: {topic['name']}")
                    break
            if not rules_found:
                logger.warning(f"❌ Tópico Regras (ID: {RULES_TOPIC_ID}) não encontrado nos tópicos descobertos")

        if WELCOME_TOPIC_ID:
            for topic in topics:
                if str(topic['id']) == str(WELCOME_TOPIC_ID):
                    welcome_found = True
                    logger.info(f"✅ Tópico Boas-vindas encontrado: {topic['name']}")
                    break
            if not welcome_found:
                logger.warning(f"❌ Tópico Boas-vindas (ID: {WELCOME_TOPIC_ID}) não encontrado nos tópicos descobertos")

        # Status geral
        if not RULES_TOPIC_ID and not WELCOME_TOPIC_ID:
            logger.warning("⚠️ Nenhum tópico configurado - bot não responderá no grupo")
        elif rules_found or welcome_found:
            logger.info("✅ Configuração funcionando - bot responderá nos tópicos configurados")
        else:
            logger.error("❌ IDs configurados mas tópicos não encontrados - verificar configuração")

        return True

    except Exception as e:
        logger.error(f"❌ Erro durante teste de configuração: {e}")
        return False

async def display_help():
    """Exibe ajuda sobre como usar o sistema de tópicos."""
    print("\n" + "="*60)
    print("🎯 SISTEMA DE DESCOBERTA DE TÓPICOS - GUIA DE USO")
    print("="*60)
    print()
    print("📋 COMANDOS DISPONÍVEIS (enviar para o bot em privado):")
    print("   /topics        - Lista todos os tópicos descobertos")
    print("   /auto_config   - Sugere configurações automáticas")
    print("   /test_topics   - Testa configuração atual")
    print()
    print("🔄 COMO DESCOBRIR TÓPICOS:")
    print("   1. Envie mensagens nos tópicos do grupo")
    print("   2. Bot identificará automaticamente os IDs")
    print("   3. Use /topics para ver a lista completa")
    print()
    print("⚙️ COMO CONFIGURAR:")
    print("   1. Use /auto_config para obter sugestões")
    print("   2. Adicione os IDs no arquivo .env:")
    print("      RULES_TOPIC_ID=\"123\"")
    print("      WELCOME_TOPIC_ID=\"456\"")
    print("   3. Reinicie o bot")
    print("   4. Use /test_topics para validar")
    print()
    print("🎮 FUNCIONAMENTO:")
    print("   • Bot responde APENAS nos tópicos configurados")
    print("   • Ignora mensagens do chat geral do grupo")
    print("   • Detecta novos membros em qualquer tópico")
    print("   • Envia boas-vindas no tópico configurado")
    print()
    print("="*60)

async def run_all_tests():
    """Executa todos os testes do sistema de tópicos."""
    logger.info(f"🧪 INICIANDO TESTES DO SISTEMA DE TÓPICOS - {datetime.now()}")

    success_count = 0
    total_tests = 2

    # Teste 1: Descoberta de tópicos
    if await test_topics_discovery():
        success_count += 1

    # Teste 2: Configuração atual
    if await test_current_configuration():
        success_count += 1

    # Exibe ajuda
    await display_help()

    # Resultado final
    logger.info(f"\n🏁 TESTES CONCLUÍDOS: {success_count}/{total_tests} sucessos")

    if success_count == total_tests:
        logger.info("✅ Todos os testes passaram!")
    else:
        logger.warning(f"⚠️ {total_tests - success_count} teste(s) falharam")

def main():
    """Função principal do script de teste."""
    setup_logging()

    # Executa os testes
    asyncio.run(run_all_tests())

if __name__ == "__main__":
    main()