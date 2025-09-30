"""
Gerenciador centralizado de tokens para API HubSoft.

Este módulo centraliza o controle de tokens OAuth para evitar:
- Múltiplas instâncias de token em módulos diferentes
- Renovação desnecessária de tokens ainda válidos
- Condições de corrida em aplicações multi-thread

Implementa singleton thread-safe com cache otimizado.
"""

import logging
import time
import threading
import requests
from typing import Optional
from urllib.parse import urljoin

from .config import (
    HUBSOFT_HOST,
    HUBSOFT_CLIENT_ID,
    HUBSOFT_CLIENT_SECRET,
    HUBSOFT_USER,
    HUBSOFT_PASSWORD,
    HUBSOFT_ENDPOINT_TOKEN
)

logger = logging.getLogger(__name__)


class HubSoftTokenManager:
    """
    Gerenciador singleton thread-safe para tokens da API HubSoft.

    Funcionalidades:
    - Token único compartilhado entre todos os módulos
    - Thread-safety com locks
    - Cache inteligente com buffer de expiração otimizado
    - Retry automático em caso de falha
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._token_lock = threading.Lock()
            self._access_token = None
            self._token_expires_at = 0
            self._token_buffer_seconds = 300  # 5 minutos de buffer
            self._last_request_time = 0
            self._min_request_interval = 1  # Mínimo 1 segundo entre requisições
            self._initialized = True

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Obtém token de acesso válido, usando cache quando possível.

        Args:
            force_refresh: Se True, força renovação mesmo com token válido

        Returns:
            str: Token de acesso válido ou None em caso de erro
        """
        with self._token_lock:
            # Verifica se token atual ainda é válido (com buffer)
            current_time = time.time()
            token_valid = (
                self._access_token and
                current_time < self._token_expires_at - self._token_buffer_seconds and
                not force_refresh
            )

            if token_valid:
                logger.debug("Usando token HubSoft em cache (válido por mais %.1f minutos)",
                           (self._token_expires_at - current_time) / 60)
                return self._access_token

            # Precisa renovar token
            return self._refresh_token()

    def _refresh_token(self) -> Optional[str]:
        """
        Renova o token de acesso fazendo nova requisição à API.

        Returns:
            str: Novo token de acesso ou None em caso de erro
        """
        current_time = time.time()

        # Rate limiting integrado: evita requisições muito frequentes
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            logger.debug(f"Token rate limiting: aguardando {wait_time:.2f}s...")
            time.sleep(wait_time)

        logger.info("Solicitando novo token de acesso HubSoft...")

        token_endpoint = urljoin(HUBSOFT_HOST, HUBSOFT_ENDPOINT_TOKEN.lstrip('/'))

        payload = {
            "grant_type": "password",
            "client_id": HUBSOFT_CLIENT_ID,
            "client_secret": HUBSOFT_CLIENT_SECRET,
            "username": HUBSOFT_USER,
            "password": HUBSOFT_PASSWORD,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Sentinela-Bot/1.0"
        }

        try:
            self._last_request_time = time.time()

            response = requests.post(
                token_endpoint,
                data=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()

            # Extrai dados do token
            new_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)  # Default 1 hora

            if not new_token:
                logger.error("Resposta da API não contém access_token")
                return None

            # Atualiza cache
            self._access_token = new_token
            self._token_expires_at = time.time() + expires_in

            logger.info("Token HubSoft renovado com sucesso (válido por %d minutos)",
                       expires_in // 60)
            logger.debug("Token expira em: %s",
                        time.strftime('%Y-%m-%d %H:%M:%S',
                                    time.localtime(self._token_expires_at)))

            return self._access_token

        except requests.exceptions.Timeout:
            logger.error("Timeout ao solicitar token HubSoft")
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Erro HTTP ao solicitar token HubSoft: %s", e)
            return None
        except (KeyError, ValueError) as e:
            logger.error("Erro ao processar resposta do token HubSoft: %s", e)
            return None
        except Exception as e:
            logger.error("Erro inesperado ao renovar token HubSoft: %s", e)
            return None

    def invalidate_token(self):
        """
        Invalida o token atual, forçando renovação na próxima requisição.

        Útil quando detectamos que o token não está funcionando.
        """
        with self._token_lock:
            logger.warning("Token HubSoft invalidado manualmente")
            self._access_token = None
            self._token_expires_at = 0

    def get_token_status(self) -> dict:
        """
        Retorna informações sobre o status atual do token.

        Returns:
            dict: Informações de status do token
        """
        with self._token_lock:
            current_time = time.time()
            has_token = self._access_token is not None

            if has_token:
                expires_in = max(0, self._token_expires_at - current_time)
                expires_in_minutes = expires_in / 60
                is_valid = current_time < self._token_expires_at - self._token_buffer_seconds
            else:
                expires_in = 0
                expires_in_minutes = 0
                is_valid = False

            return {
                "has_token": has_token,
                "is_valid": is_valid,
                "expires_in_seconds": expires_in,
                "expires_in_minutes": expires_in_minutes,
                "buffer_seconds": self._token_buffer_seconds,
                "last_refresh": time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(self._last_request_time)) if self._last_request_time else None
            }


# Instância singleton global
token_manager = HubSoftTokenManager()


def get_hubsoft_token(force_refresh: bool = False) -> Optional[str]:
    """
    Função de conveniência para obter token HubSoft.

    Args:
        force_refresh: Se True, força renovação do token

    Returns:
        str: Token válido ou None em caso de erro
    """
    return token_manager.get_access_token(force_refresh)


def invalidate_hubsoft_token():
    """
    Função de conveniência para invalidar token atual.
    """
    token_manager.invalidate_token()


def get_hubsoft_token_status() -> dict:
    """
    Função de conveniência para obter status do token.

    Returns:
        dict: Status do token
    """
    return token_manager.get_token_status()