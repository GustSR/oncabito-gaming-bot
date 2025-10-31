#!/bin/bash
#
# Auto-Update Script - GitHub Container Registry
# Verifica e atualiza bot automaticamente quando nova imagem disponível
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/auto-update.log"
REGISTRY="ghcr.io"
IMAGE_NAME="gustsr/oncabito-gaming-bot"
IMAGE_TAG="latest"
CONTAINER_NAME="oncabo-gaming-bot"
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

# Cria diretório de logs se não existir
mkdir -p "$PROJECT_DIR/logs"

# Função de log com timestamp
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# Verifica se está logado no registry
check_login() {
    if ! docker info 2>/dev/null | grep -q "Username:"; then
        if ! grep -q "$REGISTRY" ~/.docker/config.json 2>/dev/null; then
            log_error "Docker não está logado no $REGISTRY"
            log_error "Execute: echo 'SEU_TOKEN' | docker login $REGISTRY -u SEU_USUARIO --password-stdin"
            exit 1
        fi
    fi
}

# Obtém digest da imagem local
get_local_image_digest() {
    docker image inspect "$FULL_IMAGE" --format='{{index .RepoDigests 0}}' 2>/dev/null | \
        grep -oP 'sha256:[a-f0-9]+' || echo ""
}

# Obtém digest da imagem remota (registry) SEM fazer pull
get_remote_image_digest() {
    # Usa docker manifest inspect para verificar digest remoto sem baixar a imagem
    docker manifest inspect "$FULL_IMAGE" 2>/dev/null | \
        python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('config', {}).get('digest', ''))" 2>/dev/null || echo ""
}

# Verifica se container está rodando
is_container_running() {
    docker ps -q -f name="$CONTAINER_NAME" 2>/dev/null | grep -q .
}

# Verifica saúde do container
check_container_health() {
    local max_attempts=6
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if is_container_running; then
            # Verifica logs por erros críticos
            local logs=$(docker logs "$CONTAINER_NAME" --tail 20 2>&1)
            if echo "$logs" | grep -qi "error\|exception\|failed\|traceback"; then
                log_warn "Container rodando mas com possíveis erros nos logs"
                return 1
            fi
            log_success "Container está rodando e saudável"
            return 0
        fi

        log_info "Tentativa $attempt/$max_attempts - Aguardando container iniciar..."
        sleep 5
        ((attempt++))
    done

    log_error "Container não iniciou após $max_attempts tentativas"
    return 1
}

# Backup da imagem atual (para rollback)
backup_current_image() {
    if docker image inspect "$FULL_IMAGE" &>/dev/null; then
        local backup_tag="${IMAGE_TAG}-backup-$(date +%Y%m%d-%H%M%S)"
        docker tag "$FULL_IMAGE" "$REGISTRY/$IMAGE_NAME:$backup_tag"
        log_info "Backup criado: $backup_tag"
        echo "$backup_tag"
    fi
}

# Rollback para versão anterior
rollback() {
    local backup_tag=$1

    if [ -z "$backup_tag" ]; then
        log_error "Nenhum backup disponível para rollback"
        return 1
    fi

    log_warn "Iniciando rollback para versão anterior..."

    # Para container atual
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true

    # Roda versão de backup
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        --env-file "$PROJECT_DIR/.env" \
        -e TZ=America/Sao_Paulo \
        -e PYTHONUNBUFFERED=1 \
        -v "$PROJECT_DIR/data:/app/data" \
        -v "$PROJECT_DIR/logs:/app/logs" \
        "$REGISTRY/$IMAGE_NAME:$backup_tag"

    sleep 5

    if check_container_health; then
        log_success "Rollback concluído com sucesso!"
        return 0
    else
        log_error "Rollback falhou!"
        return 1
    fi
}

# Deploy da nova versão
deploy_new_version() {
    log_info "Iniciando deploy da nova versão..."

    # Cria diretórios necessários com permissões corretas
    log_info "Verificando diretórios de dados..."
    mkdir -p "$PROJECT_DIR/data/database"
    mkdir -p "$PROJECT_DIR/logs"
    # Usa 777 para garantir que o container (usuário oncabito) possa escrever
    chmod -R 777 "$PROJECT_DIR/data"
    chmod -R 777 "$PROJECT_DIR/logs"
    log_info "Diretórios criados/verificados com permissões totais (777)"

    # Para container antigo
    if is_container_running; then
        log_info "Parando container antigo..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
    fi

    # Remove container antigo
    docker rm "$CONTAINER_NAME" 2>/dev/null || true

    # Inicia novo container
    log_info "Iniciando novo container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        --env-file "$PROJECT_DIR/.env" \
        -e TZ=America/Sao_Paulo \
        -e PYTHONUNBUFFERED=1 \
        -v "$PROJECT_DIR/data:/app/data" \
        -v "$PROJECT_DIR/logs:/app/logs" \
        "$FULL_IMAGE"

    # Verifica se subiu corretamente
    if check_container_health; then
        log_success "Deploy concluído com sucesso!"

        # Mostra logs iniciais
        log_info "Logs iniciais do container:"
        docker logs "$CONTAINER_NAME" --tail 10 2>&1 | while read line; do
            log_info "  $line"
        done

        return 0
    else
        log_error "Deploy falhou - container não está saudável"
        return 1
    fi
}

# Limpeza de imagens antigas
cleanup_old_images() {
    log_info "Limpando imagens antigas..."

    # Remove imagens <none> (dangling)
    docker image prune -f &>/dev/null || true

    # Mantém apenas últimas 3 versões de backup
    local backups=$(docker images "$REGISTRY/$IMAGE_NAME" --format "{{.Tag}}" | grep "backup" | tail -n +4)
    for backup in $backups; do
        docker rmi "$REGISTRY/$IMAGE_NAME:$backup" &>/dev/null || true
        log_info "Backup antigo removido: $backup"
    done
}

# MAIN
main() {
    log_info "=========================================="
    log_info "Auto-Update iniciado"
    log_info "=========================================="

    # Verifica se Docker está rodando
    if ! docker info &>/dev/null; then
        log_error "Docker não está rodando"
        exit 1
    fi

    # Verifica se está logado no registry
    check_login

    # Obtém digest da imagem local atual
    local_digest=$(get_local_image_digest)
    if [ -z "$local_digest" ]; then
        log_info "Nenhuma imagem local encontrada - primeira execução"
        local_digest="none"
    else
        log_info "Imagem local: ${local_digest:7:12}"
    fi

    # Verifica digest da imagem remota (SEM fazer pull - apenas consulta)
    log_info "Verificando nova imagem no registry (sem pull)..."
    remote_digest=$(get_remote_image_digest)

    if [ -z "$remote_digest" ]; then
        log_error "Falha ao verificar imagem remota"
        exit 1
    fi

    log_info "Imagem remota: ${remote_digest:7:12}"

    # Compara versões
    if [ "$local_digest" = "$remote_digest" ]; then
        log_info "Já está na versão mais recente - nenhuma atualização necessária"

        # Verifica se container está rodando mesmo sem atualização
        if ! is_container_running; then
            log_warn "Container não está rodando - reiniciando..."
            deploy_new_version
        fi

        exit 0
    fi

    # Nova versão disponível!
    log_info "=========================================="
    log_info "NOVA VERSÃO DISPONÍVEL!"
    log_info "Local:  ${local_digest:7:12}"
    log_info "Remota: ${remote_digest:7:12}"
    log_info "=========================================="

    # Faz backup da versão atual
    backup_tag=$(backup_current_image)

    # Faz pull da nova versão AGORA (só quando detectar mudança)
    log_info "Baixando nova versão da imagem..."
    if ! docker pull "$FULL_IMAGE" --quiet; then
        log_error "Falha ao baixar nova imagem"
        exit 1
    fi

    # Deploy da nova versão
    if deploy_new_version; then
        log_success "=========================================="
        log_success "ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!"
        log_success "Versão anterior: ${local_digest:7:12}"
        log_success "Nova versão: ${remote_digest:7:12}"
        log_success "=========================================="

        # Limpeza
        cleanup_old_images

    else
        log_error "=========================================="
        log_error "ATUALIZAÇÃO FALHOU!"
        log_error "=========================================="

        # Tenta rollback
        if [ -n "$backup_tag" ]; then
            rollback "$backup_tag"
        else
            log_error "Impossível fazer rollback - sem backup disponível"
        fi

        exit 1
    fi
}

# Executa main
main "$@"
