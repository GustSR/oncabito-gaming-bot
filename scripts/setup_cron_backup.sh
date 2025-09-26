#!/bin/bash
# =====================================
# OnCabito Bot - Setup Cron Backup Automático
# =====================================

set -e

echo "🕰️ OnCabito Bot - Configurando Backup Automático"
echo "================================================"

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

# Obtém o diretório atual (absoluto)
PROJECT_DIR=$(pwd)
print_info "Diretório do projeto: $PROJECT_DIR"

# Verifica se o script de backup existe
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_database.sh"
if [ ! -f "$BACKUP_SCRIPT" ]; then
    print_error "Script de backup não encontrado: $BACKUP_SCRIPT"
    exit 1
fi

# Torna o script executável
chmod +x "$BACKUP_SCRIPT"
print_status "Script de backup configurado como executável"

# Verifica se o cron está instalado
if ! command -v crontab >/dev/null 2>&1; then
    print_error "Crontab não está instalado. Instale com: sudo apt-get install cron"
    exit 1
fi

# Cria entrada do cron
CRON_ENTRY="0 3 * * * cd $PROJECT_DIR && ./scripts/backup_database.sh auto >> logs/backup_cron.log 2>&1"

print_info "Configurando cron job para backup diário às 3h da manhã..."

# Verifica se a entrada já existe
if crontab -l 2>/dev/null | grep -q "backup_database.sh auto"; then
    print_warning "Cron job de backup já existe. Removendo entrada antiga..."
    crontab -l 2>/dev/null | grep -v "backup_database.sh auto" | crontab -
fi

# Adiciona nova entrada
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

print_status "Cron job adicionado com sucesso"

# Cria diretório de logs se não existir
mkdir -p "$PROJECT_DIR/logs"

# Verifica a configuração
echo ""
print_info "Verificando configuração do cron..."
echo "📋 Cron jobs atuais:"
crontab -l | grep -E "(backup_database|oncabito)" || echo "   Nenhum job encontrado"

echo ""
print_info "Configuração completa!"
echo ""
echo "🔧 Detalhes da configuração:"
echo "  • Horário: Todos os dias às 3:00 AM"
echo "  • Script: $BACKUP_SCRIPT auto"
echo "  • Logs: $PROJECT_DIR/logs/backup_cron.log"
echo "  • Retenção: 7 dias (backups automáticos)"
echo ""
echo "🧪 Para testar manualmente:"
echo "  • Backup manual: ./scripts/backup_database.sh manual"
echo "  • Ver logs: tail -f logs/backup_cron.log"
echo "  • Listar cron jobs: crontab -l"
echo ""
echo "❌ Para remover o cron job:"
echo "  • crontab -l | grep -v 'backup_database.sh auto' | crontab -"

print_status "Setup de backup automático concluído! 🎉"