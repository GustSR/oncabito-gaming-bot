#!/bin/bash
# =====================================
# OnCabito Bot - Database Restore Script
# =====================================

set -e

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

echo "🔄 OnCabito Bot - Database Restore"
echo "================================="

# Verifica parâmetros
if [ $# -eq 0 ]; then
    print_error "Uso: $0 <caminho_do_backup.db>"
    echo ""
    echo "Backups disponíveis:"
    echo ""
    echo "📁 Backups automáticos:"
    ls -lah backups/auto/*.db 2>/dev/null | awk '{print "   " $9 " (" $5 ") - " $6 " " $7 " " $8}' || echo "   Nenhum backup automático encontrado"
    echo ""
    echo "📁 Backups manuais:"
    ls -lah backups/manual/*.db 2>/dev/null | awk '{print "   " $9 " (" $5 ") - " $6 " " $7 " " $8}' || echo "   Nenhum backup manual encontrado"
    exit 1
fi

BACKUP_FILE="$1"
DB_PATH="data/database/sentinela.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Verifica se o backup existe
if [ ! -f "$BACKUP_FILE" ]; then
    print_error "Arquivo de backup não encontrado: $BACKUP_FILE"
    exit 1
fi

# Verifica integridade do backup
echo "🔍 Verificando integridade do backup..."
if sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    print_status "Backup íntegro e válido"
else
    print_error "Backup corrompido ou inválido!"
    exit 1
fi

# Mostra informações do backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -c %y "$BACKUP_FILE" 2>/dev/null || stat -f %Sm "$BACKUP_FILE" 2>/dev/null || echo "Data desconhecida")
USER_COUNT=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

echo ""
echo "📋 Informações do backup:"
echo "   • Arquivo: $BACKUP_FILE"
echo "   • Tamanho: $BACKUP_SIZE"
echo "   • Data: $BACKUP_DATE"
echo "   • Usuários: $USER_COUNT"

# Confirmação
echo ""
print_warning "ATENÇÃO: Esta operação irá substituir o banco atual!"
if [ -f "$DB_PATH" ]; then
    CURRENT_USERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    echo "   Banco atual tem: $CURRENT_USERS usuário(s)"
fi
echo ""
read -p "Tem certeza que deseja continuar? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Restore cancelado pelo usuário"
    exit 0
fi

# Backup do banco atual antes de restaurar
if [ -f "$DB_PATH" ]; then
    echo ""
    echo "💾 Fazendo backup do banco atual..."
    SAFETY_BACKUP="backups/manual/before_restore_${TIMESTAMP}.db"
    mkdir -p "$(dirname "$SAFETY_BACKUP")"
    cp "$DB_PATH" "$SAFETY_BACKUP"
    print_status "Backup de segurança criado: $SAFETY_BACKUP"
fi

# Verifica se há container rodando
CONTAINER_RUNNING=false
if docker-compose ps | grep -q "Up"; then
    CONTAINER_RUNNING=true
    print_warning "Container em execução será parado durante o restore"
fi

# Para o container se estiver rodando
if [ "$CONTAINER_RUNNING" = true ]; then
    echo ""
    echo "⏹️ Parando container..."
    docker-compose down
    print_status "Container parado"
fi

# Restaura o backup
echo ""
echo "🔄 Restaurando backup..."
mkdir -p "$(dirname "$DB_PATH")"
cp "$BACKUP_FILE" "$DB_PATH"

# Verifica se a restauração foi bem-sucedida
if [ -f "$DB_PATH" ]; then
    # Verifica integridade do banco restaurado
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
        print_status "Database restaurado com sucesso"

        # Mostra contagem de registros restaurados
        RESTORED_USERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
        echo "   • Usuários restaurados: $RESTORED_USERS"
    else
        print_error "Database restaurado mas com problemas de integridade!"
        exit 1
    fi
else
    print_error "Falha ao restaurar database"
    exit 1
fi

# Sobe o container novamente se estava rodando
if [ "$CONTAINER_RUNNING" = true ]; then
    echo ""
    echo "🆙 Reiniciando container..."
    if docker-compose up -d; then
        print_status "Container reiniciado"

        echo ""
        echo "⏳ Aguardando inicialização..."
        sleep 10

        # Verifica se o container está saudável
        if docker-compose ps | grep -q "healthy\|Up"; then
            print_status "Sistema restaurado e funcionando"
        else
            print_warning "Container iniciado mas pode não estar saudável"
            echo "📋 Logs recentes:"
            docker-compose logs --tail 10
        fi
    else
        print_error "Falha ao reiniciar container"
        print_info "Inicie manualmente com: docker-compose up -d"
    fi
fi

echo ""
print_status "Restore concluído! 🔄"
echo ""
echo "📋 Resumo:"
echo "   • Backup restaurado: $BACKUP_FILE"
echo "   • Backup de segurança: $SAFETY_BACKUP"
echo "   • Database atual: $DB_PATH"

echo ""
echo "🔧 Próximos passos:"
echo "   • Verificar funcionamento: docker-compose logs -f"
echo "   • Testar funcionalidades críticas"
echo "   • Se algo estiver errado, restaure o backup de segurança"