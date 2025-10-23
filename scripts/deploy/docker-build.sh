#!/bin/bash
# =====================================
# OnCabito Gaming Bot - Local Build Script
# =====================================

set -e

echo "🔨 OnCabito Bot - Build da Imagem Docker"
echo "========================================"

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se estamos no diretório correto
if [ ! -f "Dockerfile" ]; then
    print_error "Dockerfile não encontrado. Execute no diretório do projeto."
    exit 1
fi

# Definir tags
IMAGE_NAME="ghcr.io/gustsr/oncabito-gaming-bot"
LOCAL_TAG="oncabito-bot"

echo "🏗️ Construindo imagem Docker..."
echo "Image: $IMAGE_NAME"
echo "Local tag: $LOCAL_TAG"

# Build multi-stage com cache
if docker build \
    --tag "$IMAGE_NAME:latest" \
    --tag "$LOCAL_TAG:latest" \
    --cache-from "$IMAGE_NAME:latest" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    . ; then
    print_status "Build concluído com sucesso"
else
    print_error "Falha no build da imagem"
    exit 1
fi

# Mostrar informações da imagem
echo ""
echo "📊 Informações da imagem:"
docker images | grep -E "(oncabito-bot|oncabito-gaming-bot)" | head -5

echo ""
echo "🔍 Análise de tamanho:"
echo "Imagem: $(docker images $IMAGE_NAME:latest --format "table {{.Size}}" | tail -n +2)"
echo "Camadas: $(docker history $IMAGE_NAME:latest --format "table {{.CreatedBy}}" | wc -l)"

echo ""
echo "🧪 Testando health check..."
if docker run --rm --name oncabito-test -d "$IMAGE_NAME:latest" >/dev/null 2>&1; then
    sleep 5
    HEALTH_STATUS=$(docker inspect oncabito-test --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
    docker stop oncabito-test >/dev/null 2>&1

    if [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "no-healthcheck" ]; then
        print_status "Health check passou"
    else
        print_warning "Health check: $HEALTH_STATUS"
    fi
else
    print_warning "Não foi possível testar health check"
fi

echo ""
echo "🎯 Build concluído!"
echo ""
echo "🚀 Para usar a imagem:"
echo "  • docker run -d --name oncabito-bot $LOCAL_TAG:latest"
echo "  • docker-compose up -d (usa a imagem buildada)"
echo ""
echo "📦 Para fazer push (se autenticado):"
echo "  • docker push $IMAGE_NAME:latest"