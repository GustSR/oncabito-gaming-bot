#!/bin/bash
#
# Setup Cron - Configuração de Auto-Update
# Instala cron job para verificar atualizações a cada 10 minutos
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

# Define entrada do cron
CRON_ENTRY="*/10 * * * * $AUTO_UPDATE_SCRIPT >> $LOG_FILE 2>&1"

# Verifica se entrada já existe
if crontab -l 2>/dev/null | grep -q "auto-update.sh"; then
    echo ""
    echo -e "${YELLOW}⚠️  Cron job já existe!${NC}"
    echo ""
    echo "Cron atual:"
    crontab -l | grep "auto-update.sh"
    echo ""
    echo -e "${BLUE}Deseja substituir? (s/n)${NC}"
    read -r response

    if [[ "$response" =~ ^[Ss]$ ]]; then
        # Remove entrada antiga
        (crontab -l 2>/dev/null | grep -v "auto-update.sh") | crontab -
        echo -e "${GREEN}✅ Entrada antiga removida${NC}"
    else
        echo -e "${YELLOW}Mantendo configuração existente${NC}"
        exit 0
    fi
fi

# Adiciona nova entrada
echo ""
echo -e "${BLUE}📝 Adicionando cron job...${NC}"
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo -e "${GREEN}✅ Cron job instalado com sucesso!${NC}"
echo ""

# Mostra configuração
echo -e "${BLUE}📊 CONFIGURAÇÃO:${NC}"
echo "==========================================

"
echo "• Frequência: A cada 10 minutos"
echo "• Script: $AUTO_UPDATE_SCRIPT"
echo "• Log: $LOG_FILE"
echo ""

# Mostra próximas execuções (aproximado)
echo -e "${BLUE}⏰ PRÓXIMAS EXECUÇÕES (aproximado):${NC}"
current_minute=$(date +%M)
next_run=$((10 - current_minute % 10))
echo "• Próxima: ~$next_run minutos"
echo "• Depois: ~$((next_run + 10)) minutos"
echo "• Depois: ~$((next_run + 20)) minutos"
echo ""

# Verifica cron atual
echo -e "${BLUE}📋 CRONTAB ATUAL:${NC}"
echo "=========================================="
crontab -l | grep "auto-update" || echo "(vazio)"
echo ""

# Instruções
echo -e "${GREEN}🎉 SETUP CONCLUÍDO!${NC}"
echo ""
echo -e "${BLUE}📚 PRÓXIMOS PASSOS:${NC}"
echo ""
echo "1. Testar manualmente:"
echo "   ${YELLOW}$AUTO_UPDATE_SCRIPT${NC}"
echo ""
echo "2. Monitorar logs:"
echo "   ${YELLOW}tail -f $LOG_FILE${NC}"
echo ""
echo "3. Ver cron jobs:"
echo "   ${YELLOW}crontab -l${NC}"
echo ""
echo "4. Remover cron (se necessário):"
echo "   ${YELLOW}crontab -e${NC}"
echo "   (Remova a linha do auto-update.sh)"
echo ""
echo -e "${BLUE}ℹ️  INFORMAÇÕES:${NC}"
echo "• O script verificará atualizações a cada 10 minutos"
echo "• Apenas baixa e atualiza se houver nova versão"
echo "• Faz rollback automático se algo falhar"
echo "• Logs completos em: $LOG_FILE"
echo ""
echo -e "${GREEN}🚀 Sistema de auto-update está ativo!${NC}"
echo ""
