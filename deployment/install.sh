#!/bin/bash
#
# Script de instalação do OnCabito Bot
# Configura paths automaticamente para qualquer servidor
#

set -e

echo "🤖 ONCABITO BOT - SCRIPT DE INSTALAÇÃO"
echo "======================================"

# Detecta o diretório atual de instalação
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Diretório de instalação: $INSTALL_DIR"

# Cria variável de ambiente para o projeto
echo "🔧 Configurando variáveis de ambiente..."
if ! grep -q "ONCABITO_PROJECT_DIR" ~/.bashrc; then
    echo "export ONCABITO_PROJECT_DIR=\"$INSTALL_DIR\"" >> ~/.bashrc
    echo "✅ Variável ONCABITO_PROJECT_DIR adicionada ao ~/.bashrc"
fi

# Cria diretório de logs se não existir
if [ ! -d "$INSTALL_DIR/logs" ]; then
    mkdir -p "$INSTALL_DIR/logs"
    echo "✅ Diretório de logs criado"
fi

# Torna scripts executáveis
chmod +x "$INSTALL_DIR/deployment/run_checkup.sh"
chmod +x "$INSTALL_DIR/deployment/deploy.sh"
chmod +x "$INSTALL_DIR/scripts/"*.py
chmod +x "$INSTALL_DIR/tools/"*.sh
echo "✅ Permissões de execução configuradas"

# Atualiza o script de checkup com path dinâmico
cat > "$INSTALL_DIR/deployment/run_checkup.sh" << 'EOF'
#!/bin/bash
#
# Script para executar o checkup diário dentro do container Docker
# Usa path dinâmico baseado na localização do script
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Executando checkup diário..."
echo "Data/Hora: $(date)"
echo "Diretório: $SCRIPT_DIR"
echo "----------------------------------------"

# Executa o script dentro do container
docker exec oncabo-gaming-bot python3 scripts/tasks/daily_cpf_checkup.py

echo "----------------------------------------"
echo "✅ Checkup concluído em $(date)"
EOF

chmod +x "$INSTALL_DIR/deployment/run_checkup.sh"
echo "✅ run_checkup.sh atualizado com path dinâmico"

# Configura cron job com path dinâmico
echo "⏰ Configurando cron job..."
CRON_ENTRY="0 6 * * * $INSTALL_DIR/deployment/run_checkup.sh >> $INSTALL_DIR/logs/checkup.log 2>&1"

# Remove cron job antigo se existir
crontab -l 2>/dev/null | grep -v "OnCabito\|Sentinela\|checkup" | crontab -

# Adiciona novo cron job
(crontab -l 2>/dev/null; echo "# OnCabito Bot - Checkup diário às 6:00"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job configurado:"
echo "   $CRON_ENTRY"

# Cria script de deploy
cat > "$INSTALL_DIR/deploy.sh" << 'EOF'
#!/bin/bash
#
# Script de deploy do OnCabito Bot
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Deployando OnCabito Bot..."

# Para container se estiver rodando
if [ "$(docker ps -q -f name=oncabo-gaming-bot)" ]; then
    echo "⏹️ Parando container existente..."
    docker stop oncabo-gaming-bot
    docker rm oncabo-gaming-bot
fi

# Remove imagem antiga se existir
if [ "$(docker images -q oncabo-gaming-bot)" ]; then
    echo "🗑️ Removendo imagem antiga..."
    docker rmi oncabo-gaming-bot
fi

# Build nova imagem
echo "🔨 Buildando nova imagem..."
docker build -t oncabo-gaming-bot .

# Inicia novo container
echo "▶️ Iniciando container..."
docker run -d --name oncabo-gaming-bot \
  --env-file .env \
  -v "$SCRIPT_DIR/data:/app/data" \
  -v "$SCRIPT_DIR/logs:/app/logs" \
  oncabo-gaming-bot

echo "✅ OnCabito Bot deployado com sucesso!"
echo "📊 Status do container:"
docker ps | grep oncabo-gaming-bot

echo "📝 Para ver logs:"
echo "   docker logs oncabo-gaming-bot"
EOF

chmod +x "$INSTALL_DIR/deploy.sh"
echo "✅ Script de deploy criado"

echo ""
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "========================"
echo ""
echo "📁 Diretório do projeto: $INSTALL_DIR"
echo "⏰ Cron job: Diário às 6:00"
echo "📋 Logs: $INSTALL_DIR/logs/"
echo ""
echo "🚀 PRÓXIMOS PASSOS:"
echo "1. Configure o arquivo .env com suas credenciais"
echo "2. Execute: ./deploy.sh"
echo "3. Teste: ./run_checkup.sh"
echo ""
echo "🔄 Para recarregar variáveis de ambiente:"
echo "   source ~/.bashrc"
echo ""