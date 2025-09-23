#!/bin/bash
#
# Script para testar se o cron está funcionando
# Executa o checkup uma vez para simular a execução do cron
# Usa paths dinâmicos baseados na localização do script
#

# Detecta o diretório do projeto (parent do tools)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧪 TESTE DE CONFIGURAÇÃO CRON"
echo "=============================="
echo "📁 Diretório do projeto: $PROJECT_DIR"

echo ""
echo "📋 Verificando crontab atual:"
crontab -l | grep -E "(oncabito|checkup|Sentinela)" || echo "❌ Nenhum cron job encontrado"

echo ""
echo "📁 Verificando arquivos necessários:"
echo "- Script de execução: $(ls -la "$PROJECT_DIR/deployment/run_checkup.sh" 2>/dev/null || echo 'ERRO: Arquivo não encontrado')"
echo "- Diretório de logs: $(ls -la "$PROJECT_DIR/logs/" 2>/dev/null || echo 'ERRO: Diretório não encontrado - criando...')"

# Cria diretório de logs se não existir
if [ ! -d "$PROJECT_DIR/logs" ]; then
    mkdir -p "$PROJECT_DIR/logs"
    echo "✅ Diretório de logs criado"
fi

echo ""
echo "🚀 Executando teste do checkup (simula execução do cron):"
echo "------------------------------------------------------"

# Executa e salva no log como faria o cron
"$PROJECT_DIR/deployment/run_checkup.sh" >> "$PROJECT_DIR/logs/checkup.log" 2>&1

echo "✅ Teste concluído!"
echo ""
echo "📄 Últimas linhas do log:"
echo "------------------------"
tail -10 "$PROJECT_DIR/logs/checkup.log" 2>/dev/null || echo "ERRO: Log não encontrado"

echo ""
echo "⏰ CONFIGURAÇÃO ATUAL:"
echo "- Execução diária às 6:00 da manhã"
echo "- Logs salvos em: $PROJECT_DIR/logs/checkup.log"
echo "- Script: $PROJECT_DIR/deployment/run_checkup.sh"
echo "- Para reconfigurar: execute $PROJECT_DIR/deployment/install.sh"
echo "- Para ver logs em tempo real: tail -f $PROJECT_DIR/logs/checkup.log"