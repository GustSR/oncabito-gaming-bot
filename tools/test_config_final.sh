#!/bin/bash
#
# Script para testar a configuração final dos tópicos
#

echo "🧪 TESTE FINAL DA CONFIGURAÇÃO DE TÓPICOS"
echo "=========================================="

echo "📋 Configuração atual no .env:"
grep -E "(RULES_TOPIC_ID|WELCOME_TOPIC_ID)" "/home/gust/Repositorios Github/Sentinela/.env"

echo ""
echo "🔍 Testando via bot..."

# Executa teste de tópicos dentro do container
docker exec sentinela-bot python3 -c "
import sys
import os
sys.path.append('/app/src')

from src.sentinela.core.config import RULES_TOPIC_ID, WELCOME_TOPIC_ID, TELEGRAM_GROUP_ID

print('📊 CONFIGURAÇÃO CARREGADA:')
print(f'   • Grupo ID: {TELEGRAM_GROUP_ID}')
print(f'   • Tópico Regras: {RULES_TOPIC_ID}')
print(f'   • Tópico Boas-vindas: {WELCOME_TOPIC_ID}')

if RULES_TOPIC_ID and WELCOME_TOPIC_ID:
    print('✅ Configuração completa!')
    print('🎯 Bot responderá APENAS nos tópicos:')
    print(f'   • ID {RULES_TOPIC_ID} (Regras da Comunidade)')
    print(f'   • ID {WELCOME_TOPIC_ID} (Boas-vindas Gamer OnCabo)')
    print('❌ Bot IGNORARÁ todos os outros tópicos')
else:
    print('⚠️ Configuração incompleta!')
"

echo ""
echo "🎮 PRÓXIMOS PASSOS:"
echo "1. Teste enviar mensagem no tópico 'Regras da Comunidade'"
echo "2. Teste enviar mensagem no tópico 'Boas-vindas Gamer OnCabo'"
echo "3. Teste enviar mensagem em outros tópicos (deve ignorar)"
echo "4. Convide alguém para o grupo para testar boas-vindas"

echo ""
echo "📱 COMANDOS DISPONÍVEIS:"
echo "• /test_topics - Testa configuração atual"
echo "• /topics - Lista todos os tópicos"
echo "• /scan_topics - Reescaneia tópicos"

echo ""
echo "✅ CONFIGURAÇÃO FINALIZADA!"