#!/bin/bash
# =====================================
# OnCabito Bot - Deploy Script
# =====================================

set -e

echo "🚀 OnCabito Bot - Deploy Manual"
echo "==============================="

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

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml não encontrado. Execute no diretório do projeto."
    exit 1
fi

# 1. Atualizar código do repositório
echo "📥 Atualizando código do repositório..."
if git pull origin main; then
    print_status "Código atualizado"
else
    print_warning "Falha ao atualizar código (continuando com versão local)"
fi

# 2. Build da imagem localmente
echo "🔨 Construindo imagem Docker localmente..."
if docker build -t ghcr.io/gustsr/oncabito-gaming-bot:latest . ; then
    print_status "Imagem construída localmente"
else
    print_error "Falha ao construir imagem"
    exit 1
fi

# 3. Parar container atual
echo "⏹️  Parando container atual..."
if docker-compose down; then
    print_status "Container parado"
else
    print_warning "Container já estava parado ou erro ao parar"
fi

# 4. Criar diretórios necessários
echo "📁 Criando diretórios necessários..."
mkdir -p data/database logs backups
print_status "Diretórios criados"

# 5. Verificar .env
echo "⚙️  Verificando configuração..."
if [ ! -f ".env" ]; then
    print_error ".env não encontrado. Copie de .env.example e configure."
    exit 1
fi

# Verificar variáveis essenciais
if ! grep -q "TELEGRAM_TOKEN=" .env || ! grep -q "HUBSOFT_" .env; then
    print_error ".env incompleto. Verifique as configurações."
    exit 1
fi

print_status "Configuração verificada"

# 6. Subir nova versão
echo "🆙 Subindo nova versão..."
if docker-compose up -d; then
    print_status "Nova versão em execução"
else
    print_error "Falha ao subir nova versão"
    exit 1
fi

# 7. Aguardar inicialização
echo "⏳ Aguardando inicialização..."
sleep 10

# 8. Verificar saúde
echo "🏥 Verificando saúde do sistema..."
if docker-compose ps | grep -q "healthy"; then
    print_status "Sistema saudável"
elif docker-compose ps | grep -q "Up"; then
    print_warning "Sistema rodando (aguarde health check)"
else
    print_error "Sistema com problemas"
    echo "📋 Logs recentes:"
    docker-compose logs --tail 20
    exit 1
fi

# 9. Mostrar status final
echo ""
echo "📊 Status Final:"
docker-compose ps

echo ""
echo "📋 Logs recentes:"
docker-compose logs --tail 10

echo ""
print_status "Deploy concluído com sucesso! 🎉"
echo ""
echo "🔧 Comandos úteis:"
echo "  • Ver logs: docker-compose logs -f"
echo "  • Status: docker-compose ps"
echo "  • Parar: docker-compose down"
echo "  • Restart: docker-compose restart"