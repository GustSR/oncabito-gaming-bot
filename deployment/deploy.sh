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

# Para TODOS os containers relacionados
echo ""
echo "⏹️ Parando todos os serviços..."
echo "📦 Parando containers via docker-compose..."
COMPOSE_PROJECT_NAME=oncabito-bot docker-compose down --remove-orphans
docker-compose down --remove-orphans  # Limpa também com nome padrão

# Limpa containers antigos manualmente se existirem
echo "🧹 Limpando containers antigos..."
for container in oncabo-gaming-bot oncabito-bot sentinela-oncabito-bot-1 sentinela-oncabo-gaming-bot-1; do
    if [ "$(docker ps -aq -f name=$container)" ]; then
        echo "🗑️ Removendo container: $container"
        docker rm -f $container 2>/dev/null || true
    fi
done

# Remove imagens antigas se existirem
echo "🗑️ Removendo imagens antigas..."
for image in sentinela-oncabo-gaming-bot sentinela-oncabito-bot oncabito-bot oncabo-gaming-bot; do
    if [ "$(docker images -q $image)" ]; then
        echo "🗑️ Removendo imagem: $image"
        docker rmi $image 2>/dev/null || true
    fi
done

echo "✅ Limpeza concluída"

# Build nova imagem usando docker-compose
echo ""
echo "🔨 Buildando nova imagem..."
COMPOSE_PROJECT_NAME=oncabito-bot docker-compose build --no-cache
echo "✅ Imagem criada com sucesso"

# Cria diretórios necessários
echo ""
echo "📁 Preparando diretórios..."
mkdir -p data/database
mkdir -p logs
echo "✅ Diretórios preparados"

# Inicia novo container usando docker-compose
echo ""
echo "▶️ Iniciando OnCabito Bot..."
COMPOSE_PROJECT_NAME=oncabito-bot docker-compose up -d

# Aguarda inicialização
echo "⏳ Aguardando inicialização..."
sleep 5

# Verifica status
echo ""
echo "📊 STATUS DO DEPLOY:"
echo "===================="

if [ "$(docker ps -q -f name=oncabo-gaming-bot)" ]; then
    echo "✅ Container: ONLINE"
    echo "📦 Status: $(docker ps --format "table {{.Status}}" --filter name=oncabo-gaming-bot | tail -n1)"

    # Verifica logs iniciais
    echo ""
    echo "📋 Logs iniciais:"
    echo "----------------"
    docker logs oncabo-gaming-bot --tail 10

    echo ""
    echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
    echo ""
    echo "📊 INFORMAÇÕES ÚTEIS:"
    echo "• Container: oncabo-gaming-bot"
    echo "• Logs em tempo real: docker logs -f oncabo-gaming-bot"
    echo "• Status: docker ps | grep oncabo-gaming-bot"
    echo "• Checkup manual: $PROJECT_DIR/deployment/run_checkup.sh"
    echo "• Documentação: $PROJECT_DIR/docs/"

else
    echo "❌ ERRO: Container não iniciou corretamente"
    echo ""
    echo "🔍 LOGS DE ERRO:"
    docker logs oncabo-gaming-bot 2>/dev/null || echo "Sem logs disponíveis"
    echo ""
    echo "💡 POSSÍVEIS SOLUÇÕES:"
    echo "• Verifique as credenciais no .env"
    echo "• Teste a conexão com APIs"
    echo "• Consulte: $PROJECT_DIR/docs/DEPLOYMENT_GUIDE.md"
    exit 1
fi

echo ""
echo "🚀 OnCabito Bot está ONLINE e pronto para action! 🎮"