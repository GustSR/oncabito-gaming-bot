import os
import logging
from src.sentinela.core.config import get_env_var

logger = logging.getLogger(__name__)

# === Configurações de Conexão ===
HUBSOFT_HOST = get_env_var("HUBSOFT_HOST")
HUBSOFT_CLIENT_ID = get_env_var("HUBSOFT_CLIENT_ID")
HUBSOFT_CLIENT_SECRET = get_env_var("HUBSOFT_CLIENT_SECRET")
HUBSOFT_USER = get_env_var("HUBSOFT_USER")
HUBSOFT_PASSWORD = get_env_var("HUBSOFT_PASSWORD")

# === Endpoints da API ===
HUBSOFT_ENDPOINT_TOKEN = get_env_var("HUBSOFT_ENDPOINT_TOKEN", "/oauth/token")
HUBSOFT_ENDPOINT_CLIENTE = get_env_var("HUBSOFT_ENDPOINT_CLIENTE", "/api/v1/integracao/cliente")
HUBSOFT_ENDPOINT_ATENDIMENTO = get_env_var("HUBSOFT_ENDPOINT_ATENDIMENTO", "/api/v1/integracao/atendimento")
HUBSOFT_ENDPOINT_ATENDIMENTO_MENSAGEM = get_env_var("HUBSOFT_ENDPOINT_ATENDIMENTO_MENSAGEM", "/api/v1/integracao/atendimento/adicionar_mensagem")
HUBSOFT_ENDPOINT_ATENDIMENTO_ANEXO = get_env_var("HUBSOFT_ENDPOINT_ATENDIMENTO_ANEXO", "/api/v1/integracao/atendimento/adicionar_anexo")
HUBSOFT_ENDPOINT_CLIENTE_ATENDIMENTO = get_env_var("HUBSOFT_ENDPOINT_CLIENTE_ATENDIMENTO", "/api/v1/integracao/cliente/atendimento")

# === Configurações de Gaming ===
HUBSOFT_TIPO_ATENDIMENTO_GAMING = get_env_var("HUBSOFT_TIPO_ATENDIMENTO_GAMING", "101")
HUBSOFT_STATUS_ATENDIMENTO_ABERTO = get_env_var("HUBSOFT_STATUS_ATENDIMENTO_ABERTO", "2")

# === Mapeamento de Status ===
HUBSOFT_STATUS_MAP = {
    "1": {
        "name": "Pendente",
        "emoji": "🟣",
        "message": "Chamado registrado, aguardando análise"
    },
    "2": {
        "name": "Aguardando Análise",
        "emoji": "🟠",
        "message": "Equipe técnica está analisando seu caso"
    },
    "3": {
        "name": "Resolvido",
        "emoji": "🟢",
        "message": "Problema resolvido com sucesso"
    }
}

# Valida configurações essenciais
if not all([HUBSOFT_HOST, HUBSOFT_CLIENT_ID, HUBSOFT_CLIENT_SECRET, HUBSOFT_USER, HUBSOFT_PASSWORD]):
    logger.warning("Configurações incompletas do HubSoft - algumas funcionalidades podem não funcionar")

def get_status_display(status_id: str) -> dict:
    """Retorna informações de exibição para um status"""
    return HUBSOFT_STATUS_MAP.get(str(status_id), {
        "name": "Status Desconhecido",
        "emoji": "❓",
        "message": "Status não reconhecido"
    })

def format_protocol(atendimento_id: int) -> str:
    """
    Formata ID do atendimento para protocolo de comunicação

    Args:
        atendimento_id: ID numérico do atendimento (ex: 12345)

    Returns:
        str: Protocolo formatado (ex: "ATD12345")
    """
    if not atendimento_id:
        return "N/A"

    return f"ATD{str(atendimento_id).zfill(6)}"  # ATD000123

def extract_id_from_protocol(protocol: str) -> int:
    """
    Extrai ID numérico do protocolo formatado

    Args:
        protocol: Protocolo formatado (ex: "ATD000123", "#12345")

    Returns:
        int: ID numérico ou 0 se inválido
    """
    if not protocol:
        return 0

    # Remove prefixos comuns
    clean = protocol.replace("ATD", "").replace("#", "").strip()

    try:
        return int(clean)
    except (ValueError, TypeError):
        return 0