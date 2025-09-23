
import logging
import time
import requests
from src.sentinela.core.config import (
    HUBSOFT_HOST,
    HUBSOFT_CLIENT_ID,
    HUBSOFT_CLIENT_SECRET,
    HUBSOFT_USER,
    HUBSOFT_PASSWORD,
)

logger = logging.getLogger(__name__)

# Variáveis para cache do token em memória
_access_token = None
_token_expires_at = 0

def _get_access_token() -> str | None:
    """
    Busca um token de acesso da API Hubsoft, usando cache em memória.
    """
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at - 60:
        logger.info("Usando token de acesso da API Hubsoft em cache.")
        return _access_token

    logger.info("Token de acesso expirado ou inexistente. Solicitando um novo...")
    token_endpoint = f"{HUBSOFT_HOST}oauth/token"
    payload = {
        "grant_type": "password",
        "client_id": HUBSOFT_CLIENT_ID,
        "client_secret": HUBSOFT_CLIENT_SECRET,
        "username": HUBSOFT_USER,
        "password": HUBSOFT_PASSWORD,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(token_endpoint, data=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        _access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        _token_expires_at = time.time() + expires_in
        logger.info("Novo token de acesso obtido e armazenado em cache.")
        return _access_token
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao solicitar token de acesso da API Hubsoft: {e}")
        return None

def get_client_data(cpf: str) -> dict | None:
    """
    Busca dados completos do cliente com serviço habilitado.

    Returns:
        dict: Dados do cliente se encontrado, None caso contrário
    """
    token = _get_access_token()
    if not token:
        logger.error("Não foi possível buscar dados do cliente pois não há token de acesso.")
        return None

    formatted_cpf = "".join(filter(str.isdigit, cpf))
    api_endpoint = f"{HUBSOFT_HOST}api/v1/integracao/cliente"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "busca": "cpf_cnpj",
        "termo_busca": formatted_cpf,
        "servico_status": "servico_habilitado",
        "limit": 1
    }

    logger.info(f"Buscando dados completos do cliente na API Hubsoft...")

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
            logger.info(f"Dados do cliente encontrados com sucesso.")
            return clientes[0]  # Retorna o primeiro cliente encontrado

        logger.warning(f"Nenhum cliente encontrado para o CPF.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar dados do cliente: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar dados do cliente: {e}")
        return None

def check_contract_status(cpf: str) -> bool:
    """
    Verifica se o cliente com o CPF informado possui qualquer serviço habilitado.
    """
    token = _get_access_token()
    if not token:
        logger.error("Não foi possível verificar o contrato pois não há token de acesso.")
        return False

    formatted_cpf = "".join(filter(str.isdigit, cpf))
    api_endpoint = f"{HUBSOFT_HOST}api/v1/integracao/cliente"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "busca": "cpf_cnpj",
        "termo_busca": formatted_cpf,
        "servico_status": "servico_habilitado",
        "limit": 1  # Só precisamos saber se existe pelo menos 1
    }

    logger.info(f"Consultando API Hubsoft por cliente com serviço habilitado para o CPF.")
    logger.debug(f"URL: {api_endpoint}")
    logger.debug(f"Parâmetros: {params}")

    try:
        response = requests.get(api_endpoint, headers=headers, params=params, timeout=15)
        logger.info(f"Status da resposta: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Resposta completa da API Hubsoft: {data}")
        logger.info(f"Tipo da resposta: {type(data)}")
        if isinstance(data, list):
            logger.info(f"Quantidade de resultados: {len(data)}")
        elif isinstance(data, dict):
            logger.info(f"Chaves da resposta: {list(data.keys())}")

        # Verifica o formato da resposta e extrai os clientes
        clientes = []
        if isinstance(data, dict) and "clientes" in data:
            # Formato: {"status": "success", "clientes": [...]}
            clientes = data.get("clientes", [])
            logger.info(f"Formato de resposta com wrapper detectado. {len(clientes)} cliente(s) encontrado(s).")
        elif isinstance(data, list):
            # Formato direto: [...]
            clientes = data
            logger.info(f"Formato de resposta direto detectado. {len(clientes)} cliente(s) encontrado(s).")

        # Se encontrou pelo menos um cliente, consideramos válido
        if clientes and len(clientes) > 0:
            
            # --- LOCAL PARA FUTURA ALTERAÇÃO ---
            # Se no futuro for necessário verificar um SERVIÇO ESPECÍFICO, a lógica
            # de verificação entraria aqui. Seria algo como:
            # client_data = data[0] # Pega o primeiro cliente retornado
            # for servico in client_data.get('servicos', []):
            #     if servico.get('servico') == 'NOME_DO_SERVICO_ESPECIFICO':
            #         logger.info("Serviço específico encontrado!")
            #         return True
            # return False # Se não encontrar o serviço específico
            # -------------------------------------

            logger.info(f"Cliente com serviço habilitado encontrado para o CPF.")
            return True
        
        logger.warning(f"Nenhum cliente com serviço habilitado encontrado para o CPF.")

        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao consultar a API de integração do Hubsoft: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao processar resposta da API Hubsoft: {e}")
        return False
