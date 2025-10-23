#!/bin/bash
#
# Script para executar testes do Sentinela Bot
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${BLUE}🧪 SENTINELA BOT - EXECUÇÃO DE TESTES${NC}"
echo "=========================================="
echo ""

# Verifica se pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest não está instalado${NC}"
    echo -e "${YELLOW}💡 Instale com:${NC}"
    echo "   pip3 install -r requirements-test.txt"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ pytest encontrado: $(pytest --version)${NC}"
echo ""

# Argumentos padrão
MODE="${1:-all}"

case "$MODE" in
    "all")
        echo -e "${BLUE}📋 Executando TODOS os testes...${NC}"
        pytest tests/ -v --cov=src/sentinela --cov-report=term --cov-report=html
        ;;

    "fast")
        echo -e "${BLUE}⚡ Executando testes rápidos (sem cobertura)...${NC}"
        pytest tests/ -v
        ;;

    "critical")
        echo -e "${BLUE}🔴 Executando apenas testes críticos...${NC}"
        pytest tests/unit/locking/ tests/unit/handlers/test_permission_error_handling.py -v
        ;;

    "locks")
        echo -e "${BLUE}🔒 Executando testes de locks...${NC}"
        pytest tests/unit/locking/ -v
        ;;

    "handlers")
        echo -e "${BLUE}🎯 Executando testes de handlers...${NC}"
        pytest tests/unit/handlers/ -v
        ;;

    "entities")
        echo -e "${BLUE}📦 Executando testes de entidades...${NC}"
        pytest tests/unit/entities/ -v
        ;;

    "coverage")
        echo -e "${BLUE}📊 Gerando relatório de cobertura completo...${NC}"
        pytest tests/ --cov=src/sentinela --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✅ Relatório gerado em: htmlcov/index.html${NC}"
        ;;

    "failed")
        echo -e "${BLUE}🔄 Re-executando testes que falharam...${NC}"
        pytest --lf -v
        ;;

    "help")
        echo "Uso: ./scripts/run_tests.sh [MODO]"
        echo ""
        echo "Modos disponíveis:"
        echo "  all       - Executar todos os testes com cobertura (padrão)"
        echo "  fast      - Executar todos os testes sem cobertura (rápido)"
        echo "  critical  - Executar apenas testes críticos"
        echo "  locks     - Executar apenas testes de locks"
        echo "  handlers  - Executar apenas testes de handlers"
        echo "  entities  - Executar apenas testes de entidades"
        echo "  coverage  - Gerar relatório HTML de cobertura"
        echo "  failed    - Re-executar apenas testes que falharam"
        echo "  help      - Mostrar esta mensagem"
        echo ""
        exit 0
        ;;

    *)
        echo -e "${RED}❌ Modo inválido: $MODE${NC}"
        echo "Use: ./scripts/run_tests.sh help"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Testes concluídos!${NC}"
echo ""

# Mostrar cobertura se disponível
if [ -f ".coverage" ]; then
    echo -e "${BLUE}📊 Resumo de cobertura:${NC}"
    coverage report --fail-under=0 | tail -5 || true
fi
