#!/bin/bash
#
# OnCabito Bot - Deploy Local (Git Clone)
# Deploy usando código local com build da imagem
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detecta o diretório do projeto (parent do deployment)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${BLUE}🤖 ONCABITO BOT - DEPLOY LOCAL (PRODUÇÃO)${NC}"
echo "=============================================="
echo -e "${BLUE}📁 Projeto: $PROJECT_DIR${NC}"
echo -e "${YELLOW}📦 Modo: Build local + Imagem de produção${NC}"
echo ""

# Validações pré-deploy
echo -e "${BLUE}🔍 Validando ambiente...${NC}"

# Verifica se .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERRO: Arquivo .env não encontrado${NC}"
    echo -e "${YELLOW}💡 Configure suas credenciais primeiro:${NC}"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Verifica se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ ERRO: Docker não está rodando${NC}"
    echo -e "${YELLOW}💡 Inicie o Docker primeiro:${NC}"
    echo "   sudo systemctl start docker"
    exit 1
fi

# Verifica credenciais obrigatórias
echo -e "${BLUE}🔑 Verificando credenciais...${NC}"
if ! grep -q "^TELEGRAM_TOKEN=" .env; then
    echo -e "${RED}❌ ERRO: TELEGRAM_TOKEN não configurado${NC}"
    exit 1
fi

if ! grep -q "^TELEGRAM_GROUP_ID=" .env; then
    echo -e "${RED}❌ ERRO: TELEGRAM_GROUP_ID não configurado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ambiente validado${NC}"

# Para containers antigos
echo ""
echo -e "${BLUE}⏹️  Parando serviços antigos...${NC}"

# Para via docker-compose
if [ -f "docker-compose.yml" ]; then
    docker-compose down --remove-orphans 2>/dev/null || true
fi

# Limpa containers antigos manualmente
for container in oncabo-gaming-bot oncabo-gaming-bot-dev oncabito-bot sentinela-oncabito-bot-1 sentinela-oncabo-gaming-bot-1; do
    if [ "$(docker ps -aq -f name=$container)" ]; then
        echo -e "${YELLOW}🗑️  Removendo container: $container${NC}"
        docker rm -f $container 2>/dev/null || true
    fi
done

# Remove imagens antigas se existirem
echo -e "${BLUE}🗑️  Limpando imagens antigas...${NC}"
for image in sentinela-oncabo-gaming-bot sentinela-oncabito-bot oncabito-bot oncabo-gaming-bot; do
    if [ "$(docker images -q $image)" ]; then
        echo -e "${YELLOW}🗑️  Removendo imagem: $image${NC}"
        docker rmi $image 2>/dev/null || true
    fi
done

echo -e "${GREEN}✅ Limpeza concluída${NC}"

# Build nova imagem usando Dockerfile de PRODUÇÃO
echo ""
echo -e "${BLUE}🔨 Buildando imagem de PRODUÇÃO...${NC}"
echo -e "${YELLOW}📦 Usando: Dockerfile (multi-stage production build)${NC}"

docker build \
    --file Dockerfile \
    --tag oncabo-gaming-bot:latest \
    --tag oncabo-gaming-bot:$(date +%Y%m%d-%H%M%S) \
    --no-cache \
    .

echo -e "${GREEN}✅ Imagem criada com sucesso${NC}"

# Cria diretórios necessários
echo ""
echo -e "${BLUE}📁 Preparando diretórios...${NC}"
mkdir -p data/database
mkdir -p logs
mkdir -p backups
echo -e "${GREEN}✅ Diretórios preparados${NC}"

# Inicia novo container
echo ""
echo -e "${BLUE}▶️  Iniciando OnCabito Bot (PRODUÇÃO)...${NC}"

docker run -d \
    --name oncabo-gaming-bot \
    --restart unless-stopped \
    --env-file .env \
    -e TZ=America/Sao_Paulo \
    -e PYTHONUNBUFFERED=1 \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    oncabo-gaming-bot:latest

# Aguarda inicialização
echo -e "${YELLOW}⏳ Aguardando inicialização...${NC}"
sleep 5

# Verifica status
echo ""
echo -e "${BLUE}📊 STATUS DO DEPLOY:${NC}"
echo "===================="

if [ "$(docker ps -q -f name=oncabo-gaming-bot)" ]; then
    echo -e "${GREEN}✅ Container: ONLINE${NC}"
    echo -e "${BLUE}📦 Status: $(docker ps --format "table {{.Status}}" --filter name=oncabo-gaming-bot | tail -n1)${NC}"

    # Verifica logs iniciais
    echo ""
    echo -e "${BLUE}📋 Logs iniciais:${NC}"
    echo "----------------"
    docker logs oncabo-gaming-bot --tail 15

    echo ""
    echo -e "${GREEN}🎉 DEPLOY CONCLUÍDO COM SUCESSO!${NC}"
    echo ""
    echo -e "${BLUE}📊 INFORMAÇÕES ÚTEIS:${NC}"
    echo "• Container: oncabo-gaming-bot"
    echo "• Imagem: oncabo-gaming-bot:latest (production build)"
    echo "• Logs em tempo real: docker logs -f oncabo-gaming-bot"
    echo "• Status: docker ps | grep oncabo-gaming-bot"
    echo "• Restart: docker restart oncabo-gaming-bot"
    echo "• Stop: docker stop oncabo-gaming-bot"
    echo "• Checkup manual: $PROJECT_DIR/deployment/run_checkup.sh"
    echo "• Documentação: $PROJECT_DIR/docs/"
    echo ""
    echo -e "${BLUE}🔍 VERIFICAÇÕES RECOMENDADAS:${NC}"
    echo "1. docker logs -f oncabo-gaming-bot  # Monitore por 1-2 minutos"
    echo "2. Teste enviar /start no bot"
    echo "3. Verifique se migrations rodaram: docker exec oncabo-gaming-bot ls -la data/database/"

else
    echo -e "${RED}❌ ERRO: Container não iniciou corretamente${NC}"
    echo ""
    echo -e "${BLUE}🔍 LOGS DE ERRO:${NC}"
    docker logs oncabo-gaming-bot 2>/dev/null || echo "Sem logs disponíveis"
    echo ""
    echo -e "${YELLOW}💡 POSSÍVEIS SOLUÇÕES:${NC}"
    echo "• Verifique as credenciais no .env"
    echo "• Teste a conexão com APIs"
    echo "• Verifique se TELEGRAM_TOKEN está correto"
    echo "• Consulte: $PROJECT_DIR/docs/DEPLOYMENT_GUIDE.md"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 OnCabito Bot está ONLINE e pronto para action! 🎮${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
