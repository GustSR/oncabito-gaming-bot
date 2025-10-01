import logging
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from .config import (
    HUBSOFT_HOST,
    HUBSOFT_ENDPOINT_CLIENTE
)
from .token_manager import get_hubsoft_token
from .cache_manager import (
    cache_client_data,
    get_cached_client_data,
    cache_contract_status,
    get_cached_contract_status
)

logger = logging.getLogger(__name__)

def _get_access_token() -> Optional[str]:
    """
    DEPRECATED: Use token_manager.get_hubsoft_token() directly.

    Mantido para compatibilidade com código existente.
    Redireciona para o gerenciador centralizado de tokens.
    """
    return get_hubsoft_token()

def get_client_info(cpf: str, full_data: bool = True) -> Optional[Dict[str, Any]]:
    """
    Busca dados do cliente com serviço habilitado de forma otimizada.

    Esta função substitui get_client_data() e check_contract_status() para evitar
    requisições duplicadas à API do HubSoft.

    Args:
        cpf: CPF do cliente (formatado ou não)
        full_data: Se True retorna dados completos, se False apenas verifica existência

    Returns:
        dict: Dados do cliente se encontrado, None caso contrário
        bool: Se full_data=False, retorna apenas True/False para compatibilidade
    """
    formatted_cpf = "".join(filter(str.isdigit, cpf))

    # Tenta buscar no cache primeiro
    if full_data:
        cached_data = get_cached_client_data(formatted_cpf)
        if cached_data is not None:
            logger.debug(f"Dados do cliente {formatted_cpf[:3]}*** encontrados no cache")
            return cached_data
    else:
        cached_status = get_cached_contract_status(formatted_cpf)
        if cached_status is not None:
            logger.debug(f"Status do contrato {formatted_cpf[:3]}*** encontrado no cache: {cached_status}")
            return cached_status

    # Cache miss - busca na API
    token = _get_access_token()
    if not token:
        error_msg = "Não foi possível buscar dados do cliente pois não há token de acesso."
        logger.error(error_msg)
        return False if not full_data else None

    api_endpoint = urljoin(HUBSOFT_HOST, HUBSOFT_ENDPOINT_CLIENTE.lstrip('/'))

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "busca": "cpf_cnpj",
        "termo_busca": formatted_cpf,
        "servico_status": "servico_habilitado",
        "limit": 1
    }

    log_msg = "Verificando cliente na API Hubsoft" if not full_data else "Buscando dados completos do cliente na API Hubsoft"
    logger.info(f"{log_msg} (cache miss)...")

    try:
        response = requests.get(api_endpoint, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Extrai os clientes da resposta
        clientes = []
        if isinstance(data, dict) and "clientes" in data:
            clientes = data.get("clientes", [])
        elif isinstance(data, list):
            clientes = data

        if clientes and len(clientes) > 0:
            # Se só queremos verificar existência, cache o status e retorna True
            if not full_data:
                logger.info("Cliente com serviço habilitado encontrado para o CPF.")
                # Cache o status positivo
                cache_contract_status(formatted_cpf, True)
                return True

            # Retorna dados completos
            client_data = clientes[0]
            logger.info("Dados do cliente encontrados com sucesso.")

            # Enriquece os dados com informações úteis para atendimento
            if 'servicos' in client_data and client_data['servicos']:
                servico = client_data['servicos'][0]
                client_data['id_cliente_servico'] = servico.get('id')
                client_data['servico_nome'] = servico.get('nome', '')
                client_data['servico_status'] = servico.get('status', '')

            # Cache os dados completos
            cache_client_data(formatted_cpf, client_data)
            # Cache também o status positivo
            cache_contract_status(formatted_cpf, True)

            return client_data

        # Nenhum cliente encontrado
        warning_msg = "Nenhum cliente com serviço habilitado encontrado para o CPF." if not full_data else "Nenhum cliente encontrado para o CPF."
        logger.warning(warning_msg)

        # Cache o resultado negativo (TTL menor para casos negativos)
        if not full_data:
            cache_contract_status(formatted_cpf, False, ttl_override=30 * 60)  # 30 min para casos negativos

        return False if not full_data else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao consultar a API de integração do Hubsoft: {e}")
        return False if not full_data else None
    except Exception as e:
        error_msg = f"Erro inesperado ao processar resposta da API Hubsoft: {e}" if not full_data else f"Erro inesperado ao processar dados do cliente: {e}"
        logger.error(error_msg)
        return False if not full_data else None

# Funções de compatibilidade - mantém API existente e redireciona para função otimizada

def get_client_data(cpf: str) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Use get_client_info(cpf, full_data=True) instead.

    Mantido para compatibilidade com código existente.
    Esta função será removida em versões futuras.
    """
    logger.warning("get_client_data() is deprecated. Use get_client_info(cpf, full_data=True) instead.")
    return get_client_info(cpf, full_data=True)

def check_contract_status(cpf: str) -> bool:
    """
    DEPRECATED: Use get_client_info(cpf, full_data=False) instead.

    Verifica se o cliente com o CPF informado possui qualquer serviço habilitado.
    Esta função foi otimizada e agora reutiliza a mesma requisição da get_client_info().

    Args:
        cpf: CPF do cliente (formatado ou não)

    Returns:
        bool: True se cliente tem serviço ativo, False caso contrário
    """
    logger.warning("check_contract_status() is deprecated. Use get_client_info(cpf, full_data=False) instead.")
    return get_client_info(cpf, full_data=False)


def check_gaming_plan_by_cpf(cpf: str) -> Dict[str, Any]:
    """
    Verifica se o cliente possui plano Gaming ativo.

    Busca o cliente no HubSoft e verifica se possui algum serviço
    que contenha 'gaming', 'gamer' ou 'game' no nome do plano.

    Args:
        cpf: CPF do cliente (formatado ou não)

    Returns:
        dict: {
            'has_gaming': bool,
            'client_name': str,
            'plan_name': str,
            'service_id': int,
            'cpf': str
        }
    """
    formatted_cpf = "".join(filter(str.isdigit, cpf))

    logger.info(f"Verificando plano Gaming para CPF {formatted_cpf[:3]}***{formatted_cpf[-2:]}")

    # Busca dados completos do cliente
    client_data = get_client_info(formatted_cpf, full_data=True)

    if not client_data:
        logger.warning(f"Cliente com CPF {formatted_cpf[:3]}*** não encontrado no HubSoft")
        return {
            'has_gaming': False,
            'client_name': None,
            'plan_name': None,
            'service_id': None,
            'cpf': formatted_cpf
        }

    client_name = client_data.get('nome', client_data.get('client_name', 'Cliente'))

    # Busca serviços ativos
    services = client_data.get('servicos', [])

    if not services:
        logger.info(f"Cliente {client_name} não possui serviços ativos")
        return {
            'has_gaming': False,
            'client_name': client_name,
            'plan_name': None,
            'service_id': None,
            'cpf': formatted_cpf
        }

    # Procura por plano Gaming
    gaming_keywords = ['gaming', 'gamer', 'game']

    for service in services:
        plan_name = service.get('plano', '').lower()
        service_id = service.get('id')

        # Verifica se o plano contém alguma palavra-chave gaming
        if any(keyword in plan_name for keyword in gaming_keywords):
            logger.info(f"✅ Plano Gaming encontrado para {client_name}: {service.get('plano')}")
            return {
                'has_gaming': True,
                'client_name': client_name,
                'plan_name': service.get('plano'),
                'service_id': service_id,
                'cpf': formatted_cpf
            }

    # Nenhum plano Gaming encontrado
    logger.info(f"❌ Cliente {client_name} não possui plano Gaming")
    return {
        'has_gaming': False,
        'client_name': client_name,
        'plan_name': None,
        'service_id': None,
        'cpf': formatted_cpf
    }