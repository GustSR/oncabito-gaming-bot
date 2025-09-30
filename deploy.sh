#!/bin/bash
# =====================================
# OnCabo Gaming Bot - Deploy Local
# =====================================
# Este script faz deploy LOCAL usando código local
# CI/CD faz build e push para registry GitHub separadamente

set -e

echo "🚀 OnCabo Gaming Bot - Deploy Local"
echo "===================================="

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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

print_info "Modo: Deploy Local (usando código local)"
echo ""

# 1. Verificar se há mudanças não commitadas (opcional - apenas aviso)
echo "📝 Verificando status do Git..."
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_warning "Existem mudanças não commitadas"
    print_info "Deploy continuará com código local atual"
else
    print_status "Código sincronizado com Git"
fi
echo ""

# 2. Parar container atual
echo "⏹️  Parando container atual..."
if docker-compose down; then
    print_status "Container parado"
else
    print_warning "Container já estava parado"
fi
echo ""

# 3. Limpar recursos Docker antigos (opcional)
echo "🧹 Limpando recursos Docker não utilizados..."
docker system prune -f --volumes > /dev/null 2>&1 || true
print_status "Limpeza concluída"
echo ""

# 4. Criar diretórios necessários
echo "📁 Criando diretórios necessários..."
mkdir -p data/database logs backups
chmod 755 data logs backups
print_status "Diretórios criados e permissões ajustadas"
echo ""

# 5. Verificar .env
echo "⚙️  Verificando configuração..."
if [ ! -f ".env" ]; then
    print_error ".env não encontrado. Copie de .env.example e configure."
    echo ""
    echo "Execute: cp .env.example .env"
    echo "Depois edite .env com suas credenciais"
    exit 1
fi

# Verificar variáveis essenciais
if ! grep -q "TELEGRAM_TOKEN=" .env || grep -q "TELEGRAM_TOKEN=\"\"" .env; then
    print_error ".env incompleto. TELEGRAM_TOKEN é obrigatório."
    exit 1
fi

if ! grep -q "TELEGRAM_GROUP_ID=" .env || grep -q "TELEGRAM_GROUP_ID=\"\"" .env; then
    print_error ".env incompleto. TELEGRAM_GROUP_ID é obrigatório."
    exit 1
fi

# Verificar se HubSoft está habilitado e configurado
if grep -q "HUBSOFT_ENABLED=true" .env || grep -q "HUBSOFT_ENABLED=\"true\"" .env; then
    if ! grep -q "HUBSOFT_HOST=" .env || ! grep -q "HUBSOFT_CLIENT_ID=" .env; then
        print_warning "HubSoft habilitado mas configuração incompleta"
        print_info "Bot funcionará em modo local/mock"
    else
        print_status "Integração HubSoft configurada"
    fi
else
    print_status "HubSoft desabilitado - modo local/mock"
fi

print_status "Configuração verificada"
echo ""

# 6. Build da imagem localmente
echo "🔨 Construindo imagem Docker local..."
print_info "Usando Dockerfile e código local"

if docker-compose build --no-cache; then
    print_status "Imagem construída com sucesso"
else
    print_error "Falha ao construir imagem"
    exit 1
fi
echo ""

# 7. Subir nova versão
echo "🆙 Subindo nova versão..."
if docker-compose up -d; then
    print_status "Container iniciado em background"
else
    print_error "Falha ao subir container"
    exit 1
fi
echo ""

# 8. Aguardar inicialização
echo "⏳ Aguardando inicialização..."
for i in {1..10}; do
    echo -n "."
    sleep 1
done
echo ""
print_status "Aguardado 10 segundos"
echo ""

# 9. Verificar saúde
echo "🏥 Verificando status do container..."
sleep 2

if docker-compose ps | grep -q "Up"; then
    print_status "Container rodando"

    # Verificar health check se disponível
    if docker-compose ps | grep -q "healthy"; then
        print_status "Health check: Saudável ✓"
    elif docker-compose ps | grep -q "(healthy)"; then
        print_status "Health check: Saudável ✓"
    elif docker-compose ps | grep -q "health: starting"; then
        print_info "Health check: Iniciando..."
    else
        print_warning "Health check: Aguardando..."
    fi
else
    print_error "Container não está rodando!"
    echo ""
    echo "📋 Últimos logs:"
    docker-compose logs --tail 30
    exit 1
fi
echo ""

# 10. Mostrar status final
echo "═══════════════════════════════════"
echo "📊 Status Final"
echo "═══════════════════════════════════"
docker-compose ps
echo ""

# 11. Mostrar logs recentes
echo "═══════════════════════════════════"
echo "📋 Últimos 15 logs"
echo "═══════════════════════════════════"
docker-compose logs --tail 15
echo ""

# 12. Resumo final
echo "═══════════════════════════════════"
print_status "Deploy concluído com sucesso! 🎉"
echo "═══════════════════════════════════"
echo ""
echo "🔧 Comandos úteis:"
echo "  • Ver logs ao vivo:    docker-compose logs -f"
echo "  • Ver status:          docker-compose ps"
echo "  • Parar bot:           docker-compose down"
echo "  • Reiniciar bot:       docker-compose restart"
echo "  • Entrar no container: docker-compose exec oncabo-gaming-bot bash"
echo "  • Ver logs completos:  docker-compose logs --tail 100"
echo ""
echo "📁 Diretórios importantes:"
echo "  • Banco de dados: ./data/database/"
echo "  • Logs:          ./logs/"
echo "  • Backups:       ./backups/"
echo ""
print_info "Bot está rodando em background"
print_info "Use 'docker-compose logs -f' para acompanhar logs"
