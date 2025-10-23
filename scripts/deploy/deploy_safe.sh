#!/bin/bash
# =====================================
# OnCabito Bot - Deploy Seguro com Migrations
# =====================================

set -e

echo "🛡️ OnCabito Bot - Deploy Seguro"
echo "==============================="

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verifica se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml não encontrado. Execute no diretório do projeto."
    exit 1
fi

# 1. Backup automático antes de qualquer coisa
echo "💾 FASE 1: Backup de segurança..."
if [ -f "data/database/sentinela.db" ]; then
    if ./scripts/db/backup_database.sh auto; then
        print_status "Backup de segurança criado"
    else
        print_error "Falha no backup de segurança. Deploy cancelado por segurança."
        exit 1
    fi
else
    print_warning "Banco de dados não encontrado - primeiro deploy?"
fi

# 2. Verificar git status antes de pull
echo ""
echo "📋 FASE 2: Verificando estado do repositório..."
if git status --porcelain | grep -q .; then
    print_warning "Há mudanças locais não commitadas:"
    git status --short
    echo ""
    read -p "Continuar mesmo assim? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deploy cancelado pelo usuário"
        exit 0
    fi
fi

# 3. Atualizar código
echo ""
echo "📥 FASE 3: Atualizando código..."
if git pull origin main; then
    print_status "Código atualizado"
else
    print_warning "Falha ao atualizar código (continuando com versão local)"
fi

# 4. Executar migrations ANTES do deploy
echo ""
echo "🔄 FASE 4: Executando migrations..."
if [ -f "data/database/sentinela.db" ]; then
    print_info "Aplicando migrations ao banco existente..."

    # Executa migrations através do container se estiver rodando, senão localmente
    if docker-compose ps | grep -q "Up"; then
        print_info "Executando migrations via container..."
        if docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db; then
            print_status "Migrations aplicadas com sucesso"
        else
            print_error "Falha nas migrations. Verifique os logs."
            print_warning "Você pode restaurar o backup se necessário:"
            echo "   ./scripts/restore_database.sh backups/auto/auto_backup_*.db"
            exit 1
        fi
    else
        print_info "Container parado, executando migrations localmente..."
        if python3 migrations/migration_engine.py data/database/sentinela.db; then
            print_status "Migrations aplicadas com sucesso"
        else
            print_error "Falha nas migrations. Python3 pode não estar disponível."
            print_warning "O deploy continuará, mas execute as migrations manualmente após subir o container."
        fi
    fi
else
    print_info "Banco novo - migrations serão aplicadas na primeira inicialização"
fi

# 5. Build da imagem
echo ""
echo "🔨 FASE 5: Construindo nova imagem..."
if docker build -t ghcr.io/gustsr/oncabito-gaming-bot:latest . ; then
    print_status "Imagem construída com sucesso"
else
    print_error "Falha ao construir imagem"
    exit 1
fi

# 6. Parar container atual
echo ""
echo "⏹️ FASE 6: Parando container atual..."
if docker-compose down; then
    print_status "Container parado"
else
    print_warning "Container já estava parado ou erro ao parar"
fi

# 7. Criar diretórios necessários
echo ""
echo "📁 FASE 7: Preparando ambiente..."
mkdir -p data/database logs backups/auto backups/manual migrations
print_status "Diretórios preparados"

# 8. Verificar .env
echo ""
echo "⚙️ FASE 8: Verificando configuração..."
if [ ! -f ".env" ]; then
    print_error ".env não encontrado. Copie de .env.example e configure."
    exit 1
fi

# Verificar variáveis essenciais
if ! grep -q "TELEGRAM_TOKEN=" .env; then
    print_error ".env incompleto. TELEGRAM_TOKEN é obrigatório."
    exit 1
fi

print_status "Configuração verificada"

# 9. Subir nova versão
echo ""
echo "🆙 FASE 9: Subindo nova versão..."
if docker-compose up -d; then
    print_status "Nova versão iniciada"
else
    print_error "Falha ao subir nova versão"
    exit 1
fi

# 10. Aguardar inicialização
echo ""
echo "⏳ FASE 10: Aguardando inicialização..."
sleep 15

# 11. Executar migrations pós-deploy (garantia)
echo ""
echo "🔄 FASE 11: Verificando migrations pós-deploy..."
if docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db; then
    print_status "Migrations verificadas/aplicadas"
else
    print_warning "Falha na verificação de migrations pós-deploy"
fi

# 12. Verificar saúde do sistema
echo ""
echo "🏥 FASE 12: Verificando saúde do sistema..."
if docker-compose ps | grep -q "healthy"; then
    print_status "Sistema saudável"
elif docker-compose ps | grep -q "Up"; then
    print_warning "Sistema rodando (aguarde health check)"
else
    print_error "Sistema com problemas"
    echo "📋 Logs recentes:"
    docker-compose logs --tail 20
    print_warning "Considere fazer rollback se o problema persistir"
    exit 1
fi

# 13. Teste básico de funcionalidade
echo ""
echo "🧪 FASE 13: Teste básico de funcionalidade..."
USER_COUNT=$(docker exec oncabito-bot python3 /app/scripts/diagnostics/health_check.py 2>/dev/null || echo "-1")

if [ "$USER_COUNT" -ge 0 ]; then
    print_status "Database acessível - $USER_COUNT usuário(s) ativo(s)"
else
    print_warning "Não foi possível verificar database"
fi

# 14. Status final
echo ""
echo "📊 FASE 14: Status final..."
docker-compose ps

echo ""
echo "📋 Logs recentes:"
docker-compose logs --tail 10

echo ""
print_status "Deploy seguro concluído com sucesso! 🎉"
echo ""
echo "🔧 Comandos úteis:"
echo "  • Ver logs: docker-compose logs -f"
echo "  • Status: docker-compose ps"
echo "  • Backup manual: ./scripts/db/backup_database.sh"
echo "  • Verificar migrations: docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db"

echo ""
print_info "Se algo der errado, você pode restaurar o backup automático criado no início do deploy."