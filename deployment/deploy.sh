#!/bin/bash
#
# OnCabito Bot - Deploy Script
# Deploy automatizado com estrutura organizada
#

set -e

# Detecta o diretório do projeto (parent do deployment)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "🤖 ONCABITO BOT - DEPLOY AUTOMATIZADO"
echo "====================================="
echo "📁 Projeto: $PROJECT_DIR"

# Validações pré-deploy
echo ""
echo "🔍 Validando ambiente..."

# Verifica se .env existe
if [ ! -f ".env" ]; then
    echo "❌ ERRO: Arquivo .env não encontrado"
    echo "💡 Configure suas credenciais primeiro:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Verifica se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERRO: Docker não está rodando"
    echo "💡 Inicie o Docker primeiro:"
    echo "   sudo systemctl start docker"
    exit 1
fi

# Verifica credenciais obrigatórias
echo "🔑 Verificando credenciais..."
if ! grep -q "^TELEGRAM_TOKEN=" .env || ! grep -q "^HUBSOFT_HOST=" .env; then
    echo "❌ ERRO: Credenciais obrigatórias não configuradas"
    echo "💡 Configure no .env:"
    echo "   TELEGRAM_TOKEN=seu_token"
    echo "   HUBSOFT_HOST=sua_api"
    exit 1
fi

echo "✅ Ambiente validado"

# Para container se estiver rodando
echo ""
echo "⏹️ Parando serviços..."
if [ "$(docker ps -q -f name=oncabito-bot)" ]; then
    echo "📦 Parando container existente..."
    docker stop oncabito-bot
    docker rm oncabito-bot
    echo "✅ Container parado"
else
    echo "ℹ️ Nenhum container rodando"
fi

# Remove imagem antiga se existir
if [ "$(docker images -q oncabito-bot)" ]; then
    echo "🗑️ Removendo imagem antiga..."
    docker rmi oncabito-bot
    echo "✅ Imagem antiga removida"
fi

# Build nova imagem
echo ""
echo "🔨 Buildando nova imagem..."
docker build -t oncabito-bot .
echo "✅ Imagem criada com sucesso"

# Cria diretórios necessários
echo ""
echo "📁 Preparando diretórios..."
mkdir -p data/database
mkdir -p logs
echo "✅ Diretórios preparados"

# Inicia novo container
echo ""
echo "▶️ Iniciando OnCabito Bot..."
docker run -d --name oncabito-bot \
  --restart unless-stopped \
  --env-file .env \
  -v "$PROJECT_DIR/data:/app/data" \
  -v "$PROJECT_DIR/logs:/app/logs" \
  oncabito-bot

# Aguarda inicialização
echo "⏳ Aguardando inicialização..."
sleep 5

# Verifica status
echo ""
echo "📊 STATUS DO DEPLOY:"
echo "===================="

if [ "$(docker ps -q -f name=oncabito-bot)" ]; then
    echo "✅ Container: ONLINE"
    echo "📦 Status: $(docker ps --format "table {{.Status}}" --filter name=oncabito-bot | tail -n1)"

    # Verifica logs iniciais
    echo ""
    echo "📋 Logs iniciais:"
    echo "----------------"
    docker logs oncabito-bot --tail 10

    echo ""
    echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
    echo ""
    echo "📊 INFORMAÇÕES ÚTEIS:"
    echo "• Container: oncabito-bot"
    echo "• Logs em tempo real: docker logs -f oncabito-bot"
    echo "• Status: docker ps | grep oncabito-bot"
    echo "• Checkup manual: $PROJECT_DIR/deployment/run_checkup.sh"
    echo "• Documentação: $PROJECT_DIR/docs/"

else
    echo "❌ ERRO: Container não iniciou corretamente"
    echo ""
    echo "🔍 LOGS DE ERRO:"
    docker logs oncabito-bot 2>/dev/null || echo "Sem logs disponíveis"
    echo ""
    echo "💡 POSSÍVEIS SOLUÇÕES:"
    echo "• Verifique as credenciais no .env"
    echo "• Teste a conexão com APIs"
    echo "• Consulte: $PROJECT_DIR/docs/DEPLOYMENT_GUIDE.md"
    exit 1
fi

echo ""
echo "🚀 OnCabito Bot está ONLINE e pronto para action! 🎮"