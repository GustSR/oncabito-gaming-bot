#!/bin/bash
# =====================================
# OnCabito Bot - Setup Completo de Monitoramento
# =====================================

set -e

echo "🛡️ OnCabito Bot - Setup de Monitoramento Completo"
echo "=================================================="

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

PROJECT_DIR=$(pwd)
print_info "Projeto: $PROJECT_DIR"

# Verifica se o cron está instalado
if ! command -v crontab >/dev/null 2>&1; then
    print_error "Crontab não está instalado. Instale com: sudo apt-get install cron"
    exit 1
fi

# Cria diretórios necessários
mkdir -p logs backups/auto backups/manual backups/critical_data
print_status "Diretórios preparados"

# Torna scripts executáveis
chmod +x scripts/*.sh
chmod +x scripts/*.py
print_status "Scripts configurados como executáveis"

# Remove cron jobs antigos relacionados ao projeto
print_info "Removendo cron jobs antigos..."
crontab -l 2>/dev/null | grep -v "backup_database.sh\|verify_data_integrity.py\|export_critical_data.py" | crontab -

# Configura novos cron jobs
print_info "Configurando novos cron jobs..."

# Backup diário às 3h
BACKUP_CRON="0 3 * * * cd $PROJECT_DIR && ./scripts/db/backup_database.sh auto >> logs/backup_cron.log 2>&1"

# Verificação de integridade às 6h
INTEGRITY_CRON="0 6 * * * cd $PROJECT_DIR && python3 ./scripts/verify_data_integrity.py >> logs/integrity_cron.log 2>&1"

# Export de dados críticos às 9h
EXPORT_CRON="0 9 * * * cd $PROJECT_DIR && python3 ./scripts/export_critical_data.py >> logs/export_cron.log 2>&1"

# Adiciona todos os cron jobs
{
    crontab -l 2>/dev/null
    echo "$BACKUP_CRON"
    echo "$INTEGRITY_CRON"
    echo "$EXPORT_CRON"
} | crontab -

print_status "Cron jobs configurados"

# Cria arquivos de log vazios se não existirem
touch logs/backup_cron.log logs/integrity_cron.log logs/export_cron.log
print_status "Arquivos de log criados"

# Testa scripts
print_info "Testando scripts..."

echo "📦 Testando backup manual..."
if ./scripts/db/backup_database.sh manual; then
    print_status "Script de backup funcionando"
else
    print_warning "Script de backup teve problemas"
fi

echo "🔍 Testando verificação de integridade..."
if python3 ./scripts/verify_data_integrity.py; then
    print_status "Script de integridade funcionando"
else
    print_warning "Script de integridade teve problemas"
fi

echo "📊 Testando export de dados críticos..."
if python3 ./scripts/export_critical_data.py; then
    print_status "Script de export funcionando"
else
    print_warning "Script de export teve problemas"
fi

# Mostra configuração final
echo ""
print_info "📋 CONFIGURAÇÃO FINALIZADA"
echo ""
echo "🕐 CRONOGRAMA AUTOMÁTICO:"
echo "  • 03:00 - Backup automático diário"
echo "  • 06:00 - Verificação de integridade"
echo "  • 09:00 - Export de dados críticos"
echo ""
echo "📁 ARQUIVOS E DIRETÓRIOS:"
echo "  • Backups SQLite: backups/auto/ e backups/manual/"
echo "  • Dados críticos: backups/critical_data/"
echo "  • Logs gerais: logs/"
echo "  • Logs de cron: logs/*_cron.log"
echo ""
echo "🔧 COMANDOS ÚTEIS:"
echo "  • Ver cron jobs: crontab -l"
echo "  • Backup manual: ./scripts/db/backup_database.sh manual"
echo "  • Verificação manual: python3 ./scripts/verify_data_integrity.py"
echo "  • Export manual: python3 ./scripts/export_critical_data.py"
echo "  • Ver logs: tail -f logs/backup_cron.log"
echo ""
echo "📊 VERIFICAR STATUS:"
echo "  • Últimos backups: ls -la backups/auto/"
echo "  • Histórico integridade: cat logs/integrity_history.json"
echo "  • Exports disponíveis: ls -la backups/critical_data/"
echo ""
echo "❌ REMOVER MONITORAMENTO:"
echo "  • crontab -l | grep -v '$PROJECT_DIR' | crontab -"

print_status "Setup de monitoramento completo instalado! 🎉"

echo ""
print_info "💡 PRÓXIMOS PASSOS:"
echo "  1. Os scripts rodarão automaticamente conforme cronograma"
echo "  2. Monitore logs em: tail -f logs/*_cron.log"
echo "  3. Verifique se backups estão sendo criados: ls backups/auto/"
echo "  4. Em caso de problemas, consulte logs específicos"
echo ""
print_warning "⚠️  Para funcionar corretamente, mantenha o servidor ligado nos horários programados!"