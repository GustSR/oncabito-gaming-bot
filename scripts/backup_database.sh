#!/bin/bash
# =====================================
# OnCabito Bot - Database Backup Script
# =====================================

set -e

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

echo "💾 OnCabito Bot - Database Backup"
echo "================================="

# Configurações
DB_PATH="data/database/sentinela.db"
BACKUP_DIR="backups"
AUTO_BACKUP_DIR="$BACKUP_DIR/auto"
MANUAL_BACKUP_DIR="$BACKUP_DIR/manual"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Tipo de backup (auto ou manual)
BACKUP_TYPE="${1:-manual}"

if [ "$BACKUP_TYPE" = "auto" ]; then
    DEST_DIR="$AUTO_BACKUP_DIR"
    BACKUP_NAME="auto_backup_${TIMESTAMP}.db"
    RETENTION_DAYS=7
else
    DEST_DIR="$MANUAL_BACKUP_DIR"
    BACKUP_NAME="manual_backup_${TIMESTAMP}.db"
    RETENTION_DAYS=30
fi

# Verifica se o banco existe
if [ ! -f "$DB_PATH" ]; then
    print_error "Banco de dados não encontrado: $DB_PATH"
    exit 1
fi

# Cria diretórios de backup
mkdir -p "$DEST_DIR"

# Verifica se há container rodando
CONTAINER_RUNNING=false
if docker-compose ps | grep -q "Up"; then
    CONTAINER_RUNNING=true
    echo "🐳 Container detectado em execução"
fi

# Faz backup
echo "📦 Criando backup..."
if [ "$CONTAINER_RUNNING" = true ]; then
    # Tenta backup via sqlite3 no container, se falhar usa cópia direta
    if docker exec oncabito-bot sqlite3 /app/data/database/sentinela.db ".backup /app/data/database/backup_temp.db" 2>/dev/null; then
        docker cp oncabito-bot:/app/data/database/backup_temp.db "$DEST_DIR/$BACKUP_NAME"
        docker exec oncabito-bot rm -f /app/data/database/backup_temp.db
        echo "   Backup via SQLite3 no container"
    else
        # Fallback: cópia direta do arquivo
        print_warning "SQLite3 não disponível no container, usando cópia direta"
        cp "$DB_PATH" "$DEST_DIR/$BACKUP_NAME"
        echo "   Backup via cópia direta"
    fi
else
    # Backup direto (container parado)
    cp "$DB_PATH" "$DEST_DIR/$BACKUP_NAME"
    echo "   Backup direto (container parado)"
fi

# Verifica se o backup foi criado
if [ -f "$DEST_DIR/$BACKUP_NAME" ]; then
    BACKUP_SIZE=$(du -h "$DEST_DIR/$BACKUP_NAME" | cut -f1)
    print_status "Backup criado: $DEST_DIR/$BACKUP_NAME ($BACKUP_SIZE)"
else
    print_error "Falha ao criar backup"
    exit 1
fi

# Verifica integridade do backup
echo "🔍 Verificando integridade do backup..."
if command -v sqlite3 >/dev/null 2>&1; then
    if sqlite3 "$DEST_DIR/$BACKUP_NAME" "PRAGMA integrity_check;" | grep -q "ok"; then
        print_status "Integridade do backup verificada"
    else
        print_error "Backup corrompido!"
        rm -f "$DEST_DIR/$BACKUP_NAME"
        exit 1
    fi
    # Conta registros no backup para verificação adicional
    RECORD_COUNT=$(sqlite3 "$DEST_DIR/$BACKUP_NAME" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
else
    print_warning "SQLite3 não disponível para verificação de integridade"
    print_status "Backup criado (verificação básica de tamanho)"
    RECORD_COUNT="N/A"
fi
echo "📊 Registros de usuários no backup: $RECORD_COUNT"

# Limpeza de backups antigos
echo "🧹 Removendo backups antigos (>$RETENTION_DAYS dias)..."
REMOVED_COUNT=$(find "$DEST_DIR" -name "*.db" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$REMOVED_COUNT" -gt 0 ]; then
    print_status "Removidos $REMOVED_COUNT backup(s) antigo(s)"
else
    echo "   Nenhum backup antigo para remover"
fi

# Lista backups atuais
echo ""
echo "📋 Backups disponíveis em $DEST_DIR:"
ls -lah "$DEST_DIR"/*.db 2>/dev/null | awk '{print "   " $9 " (" $5 ") - " $6 " " $7 " " $8}' || echo "   Nenhum backup encontrado"

echo ""
print_status "Backup concluído com sucesso! 💾"

# Se for backup automático, não mostra comandos
if [ "$BACKUP_TYPE" != "auto" ]; then
    echo ""
    echo "🔧 Comandos úteis:"
    echo "  • Backup automático: ./scripts/backup_database.sh auto"
    echo "  • Restaurar backup: ./scripts/restore_database.sh $DEST_DIR/$BACKUP_NAME"
    echo "  • Listar backups: ls -la $BACKUP_DIR/"
fi