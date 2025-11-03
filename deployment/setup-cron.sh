#!/bin/bash
#
# Setup Cron - Configuração de Todos os Cron Jobs
# Instala cron jobs de auto-update E verificações diárias
#

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AUTO_UPDATE_SCRIPT="$SCRIPT_DIR/auto-update.sh"
LOG_FILE="$PROJECT_DIR/logs/auto-update.log"

echo -e "${BLUE}🔧 SETUP CRON - AUTO-UPDATE${NC}"
echo "=========================================="
echo ""

# Verifica se auto-update.sh existe
if [ ! -f "$AUTO_UPDATE_SCRIPT" ]; then
    echo -e "${RED}❌ ERRO: auto-update.sh não encontrado${NC}"
    echo -e "${YELLOW}Localização esperada: $AUTO_UPDATE_SCRIPT${NC}"
    exit 1
fi

# Torna script executável
chmod +x "$AUTO_UPDATE_SCRIPT"
echo -e "${GREEN}✅ Script auto-update.sh está executável${NC}"

# Cria diretórios necessários com permissões corretas
mkdir -p "$PROJECT_DIR/data/database"
mkdir -p "$PROJECT_DIR/logs"
# Usa 777 para garantir que o container (usuário oncabito) possa escrever
chmod -R 777 "$PROJECT_DIR/data"
chmod -R 777 "$PROJECT_DIR/logs"
echo -e "${GREEN}✅ Diretórios de dados e logs criados com permissões totais (777)${NC}"

# Verifica se cron está instalado
if ! command -v crontab &> /dev/null; then
    echo -e "${RED}❌ ERRO: crontab não está instalado${NC}"
    echo -e "${YELLOW}💡 Instale com:${NC}"
    echo "   Ubuntu/Debian: sudo apt install cron"
    echo "   CentOS/RHEL: sudo yum install cronie"
    exit 1
fi

echo -e "${GREEN}✅ crontab está instalado${NC}"

# Verifica se outros scripts existem
CHECKUP_SCRIPT="$SCRIPT_DIR/run_checkup.sh"
INTEGRITY_SCRIPT="$SCRIPT_DIR/run_integrity_check.sh"
EXPORT_SCRIPT="$SCRIPT_DIR/run_data_export.sh"

# Torna todos os scripts executáveis
chmod +x "$CHECKUP_SCRIPT" 2>/dev/null || true
chmod +x "$INTEGRITY_SCRIPT" 2>/dev/null || true
chmod +x "$EXPORT_SCRIPT" 2>/dev/null || true

# Define entradas dos cron jobs
# Auto-Update: A cada 10 min, MAS apenas entre 00:00 e 05:00 (madrugada)
# Evita conflito com jobs de verificação que rodam durante o dia
CRON_AUTO_UPDATE="*/10 0-5 * * * $AUTO_UPDATE_SCRIPT >> $LOG_FILE 2>&1"
# Checkup: A cada 30 minutos das 6:00 até 23:59 (processa conflitos mais rapidamente)
CRON_CHECKUP="*/30 6-23 * * * $CHECKUP_SCRIPT >> $PROJECT_DIR/logs/checkup.log 2>&1"
CRON_INTEGRITY="0 6 * * * $INTEGRITY_SCRIPT >> $PROJECT_DIR/logs/integrity.log 2>&1"
CRON_EXPORT="30 6 * * * $EXPORT_SCRIPT >> $PROJECT_DIR/logs/export.log 2>&1"

# Verifica se entrada já existe
if crontab -l 2>/dev/null | grep -q "auto-update.sh\|run_checkup.sh"; then
    echo ""
    echo -e "${YELLOW}⚠️  Cron jobs já existem!${NC}"
    echo ""
    echo "Cron jobs atuais:"
    crontab -l | grep -E "auto-update.sh|run_checkup.sh|run_integrity|run_data_export" || echo "(nenhum)"
    echo ""
    echo -e "${BLUE}Deseja substituir TODOS os cron jobs? (s/n)${NC}"
    read -r response

    if [[ "$response" =~ ^[Ss]$ ]]; then
        # Remove entradas antigas
        (crontab -l 2>/dev/null | grep -v "auto-update.sh\|run_checkup.sh\|run_integrity\|run_data_export\|OnCabo\|Sentinela") | crontab -
        echo -e "${GREEN}✅ Entradas antigas removidas${NC}"
    else
        echo -e "${YELLOW}Mantendo configuração existente${NC}"
        exit 0
    fi
fi

# Adiciona novas entradas
echo ""
echo -e "${BLUE}📝 Adicionando cron jobs...${NC}"
(crontab -l 2>/dev/null; echo ""; echo "# OnCabo Gaming Bot - Automated Tasks"; echo "$CRON_AUTO_UPDATE"; echo "$CRON_CHECKUP"; echo "$CRON_INTEGRITY"; echo "$CRON_EXPORT") | crontab -

echo -e "${GREEN}✅ Todos os cron jobs instalados com sucesso!${NC}"
echo ""

# Mostra configuração
echo -e "${BLUE}📊 CONFIGURAÇÃO:${NC}"
echo "=========================================="
echo ""
echo "✅ Auto-Update (Deploy Automático)"
echo "   Frequência: A cada 10 minutos (00:00-05:00 apenas)"
echo "   Script: $AUTO_UPDATE_SCRIPT"
echo "   Log: $LOG_FILE"
echo ""
echo "✅ Daily CPF Checkup"
echo "   Frequência: A cada 30 minutos (6:00-23:59)"
echo "   Script: $CHECKUP_SCRIPT"
echo "   Log: $PROJECT_DIR/logs/checkup.log"
echo ""
echo "✅ Data Integrity Check"
echo "   Frequência: Diário às 6:00 AM"
echo "   Script: $INTEGRITY_SCRIPT"
echo "   Log: $PROJECT_DIR/logs/integrity.log"
echo ""
echo "✅ Critical Data Export"
echo "   Frequência: Diário às 6:30 AM"
echo "   Script: $EXPORT_SCRIPT"
echo "   Log: $PROJECT_DIR/logs/export.log"
echo ""

# Verifica cron atual
echo -e "${BLUE}📋 CRONTAB ATUAL:${NC}"
echo "=========================================="
crontab -l | grep -E "auto-update|run_checkup|run_integrity|run_data_export" || echo "(vazio)"
echo ""

# Instruções
echo -e "${GREEN}🎉 SETUP CONCLUÍDO!${NC}"
echo ""
echo -e "${BLUE}📚 PRÓXIMOS PASSOS:${NC}"
echo ""
echo "1. Testar manualmente:"
echo "   ${YELLOW}$AUTO_UPDATE_SCRIPT${NC}"
echo "   ${YELLOW}$CHECKUP_SCRIPT${NC}"
echo "   ${YELLOW}$INTEGRITY_SCRIPT${NC}"
echo "   ${YELLOW}$EXPORT_SCRIPT${NC}"
echo ""
echo "2. Monitorar logs:"
echo "   ${YELLOW}tail -f $PROJECT_DIR/logs/checkup.log${NC}"
echo "   ${YELLOW}tail -f $PROJECT_DIR/logs/integrity.log${NC}"
echo "   ${YELLOW}tail -f $PROJECT_DIR/logs/export.log${NC}"
echo "   ${YELLOW}tail -f $LOG_FILE${NC}"
echo ""
echo "3. Ver cron jobs:"
echo "   ${YELLOW}crontab -l${NC}"
echo ""
echo "4. Editar cron jobs:"
echo "   ${YELLOW}crontab -e${NC}"
echo ""
echo -e "${BLUE}ℹ️  INFORMAÇÕES:${NC}"
echo "• Auto-update: Verifica atualizações a cada 10 min (00:00-05:00)"
echo "• Checkup: Verifica CPFs, contratos, remove inativos (cada 30 min, 6:00-23:59)"
echo "• Integrity: Monitora saúde do banco de dados (6:00 AM)"
echo "• Export: Backup incremental dos dados (6:30 AM)"
echo "• Logs completos em: $PROJECT_DIR/logs/"
echo ""
echo -e "${YELLOW}⚠️  DEPLOY MANUAL:${NC}"
echo "Para atualizar fora do horário automático (6:00-23:59):"
echo "  ${YELLOW}$AUTO_UPDATE_SCRIPT${NC}"
echo "  ou: ${YELLOW}$SCRIPT_DIR/../deploy.sh${NC} (se existir)"
echo ""
echo -e "${GREEN}🚀 Sistema de automação está ativo!${NC}"
echo ""
