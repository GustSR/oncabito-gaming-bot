#!/bin/bash
#
# OnCabito Bot - Development Script
# Comandos rápidos para desenvolvimento
#

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções auxiliares
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Comandos disponíveis
show_help() {
    cat << EOF
🤖 OnCabito Bot - Development Helper

COMANDOS DISPONÍVEIS:

  ./dev.sh start       - Inicia o bot em modo desenvolvimento
  ./dev.sh stop        - Para o bot
  ./dev.sh restart     - Reinicia o bot (rápido, sem rebuild)
  ./dev.sh rebuild     - Rebuild completo da imagem dev
  ./dev.sh logs        - Mostra logs em tempo real
  ./dev.sh shell       - Abre shell no container
  ./dev.sh status      - Verifica status do container
  ./dev.sh clean       - Remove container e volumes dev

DICAS:

  • Mudanças no código são refletidas com 'restart' (sem rebuild)
  • Use 'rebuild' apenas quando mudar requirements.txt
  • Para produção, use: ./deployment/deploy.sh

EOF
}

DOCKER_COMPOSE="docker-compose -f docker-compose.yml"

# Funções principais
cmd_start() {
    log_info "Iniciando bot em modo desenvolvimento..."

    if [ ! -f ".env" ]; then
        log_error "Arquivo .env não encontrado"
        log_warning "Execute: cp .env.example .env && nano .env"
        exit 1
    fi

    $DOCKER_COMPOSE up -d
    sleep 2

    if [ "$(docker ps -q -f name=oncabo-gaming-bot-dev)" ]; then
        log_success "Bot iniciado em modo DEV"
        log_info "Container: oncabo-gaming-bot-dev"
        log_info "Logs: ./dev.sh logs"
    else
        log_error "Falha ao iniciar bot"
        $DOCKER_COMPOSE logs
        exit 1
    fi
}

cmd_stop() {
    log_info "Parando bot..."
    $DOCKER_COMPOSE stop
    log_success "Bot parado"
}

cmd_restart() {
    log_info "Reiniciando bot (rápido, sem rebuild)..."
    $DOCKER_COMPOSE restart
    sleep 2
    log_success "Bot reiniciado com código atualizado"
    log_info "Logs: ./dev.sh logs"
}

cmd_rebuild() {
    log_info "Fazendo rebuild da imagem dev..."
    $DOCKER_COMPOSE down
    $DOCKER_COMPOSE build --no-cache
    $DOCKER_COMPOSE up -d
    sleep 2
    log_success "Rebuild completo e bot reiniciado"
}

cmd_logs() {
    log_info "Mostrando logs (Ctrl+C para sair)..."
    $DOCKER_COMPOSE logs -f --tail=50
}

cmd_shell() {
    log_info "Abrindo shell no container..."
    $DOCKER_COMPOSE exec oncabo-gaming-bot /bin/bash
}

cmd_status() {
    echo ""
    log_info "STATUS DO AMBIENTE DEV"
    echo "======================"

    if [ "$(docker ps -q -f name=oncabo-gaming-bot-dev)" ]; then
        log_success "Container: ONLINE"
        echo ""
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter name=oncabo-gaming-bot-dev
        echo ""
        log_info "Últimas 10 linhas do log:"
        docker logs oncabo-gaming-bot-dev --tail 10
    else
        log_warning "Container: OFFLINE"
        echo ""
        log_info "Para iniciar: ./dev.sh start"
    fi
    echo ""
}

cmd_clean() {
    log_warning "Isso irá remover o container e volumes dev"
    read -p "Confirma? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Limpando ambiente dev..."
        $DOCKER_COMPOSE down -v
        log_success "Ambiente dev limpo"
    else
        log_info "Operação cancelada"
    fi
}

# Main
case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    rebuild)
        cmd_rebuild
        ;;
    logs)
        cmd_logs
        ;;
    shell)
        cmd_shell
        ;;
    status)
        cmd_status
        ;;
    clean)
        cmd_clean
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Comando desconhecido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
