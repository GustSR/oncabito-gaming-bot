"""
HubSoft API Service Implementation.

Implementa comunicação real com a API do HubSoft,
incluindo autenticação, rate limiting e cache.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import aiohttp
import hashlib
import json

from ...domain.repositories.hubsoft_repository import (
    HubSoftAPIRepository,
    HubSoftCacheRepository,
    HubSoftAPIError
)
from ...integrations.hubsoft.rate_limiter import RateLimiter
from ...integrations.hubsoft.token_manager import TokenManager
from ...integrations.hubsoft.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class HubSoftAPIService(HubSoftAPIRepository):
    """Implementação do serviço de API HubSoft."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        rate_limiter: Optional[RateLimiter] = None,
        token_manager: Optional[TokenManager] = None,
        timeout_seconds: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds

        # Componentes auxiliares
        self.rate_limiter = rate_limiter or RateLimiter()
        self.token_manager = token_manager or TokenManager()

        # Session HTTP reutilizável
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém session HTTP reutilizável."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'OnCabo-Sentinela/1.0'
                }
            )
        return self._session

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        authenticated: bool = True
    ) -> Dict[str, Any]:
        """Faz requisição para a API HubSoft."""

        # Rate limiting
        await self.rate_limiter.acquire()

        try:
            session = await self._get_session()
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

            # Headers da requisição
            headers = {}

            if authenticated:
                token = await self.token_manager.get_valid_token()
                if not token:
                    # Faz login se necessário
                    token = await self._authenticate()

                headers['Authorization'] = f'Bearer {token}'

            # Faz a requisição
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            ) as response:

                # Verifica rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await self.rate_limiter.handle_rate_limit(retry_after)
                    raise HubSoftAPIError(
                        "Rate limit exceeded",
                        status_code=429,
                        error_code="rate_limit_exceeded"
                    )

                # Lê resposta
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}

                # Verifica se houve erro
                if not response.ok:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    error_code = response_data.get('error_code', 'api_error')

                    raise HubSoftAPIError(
                        error_message,
                        status_code=response.status,
                        error_code=error_code,
                        details=response_data
                    )

                return response_data

        except aiohttp.ClientError as e:
            raise HubSoftAPIError(
                f"Connection error: {str(e)}",
                error_code="connection_error"
            )
        except asyncio.TimeoutError:
            raise HubSoftAPIError(
                "Request timeout",
                error_code="timeout"
            )

    async def _authenticate(self) -> str:
        """Faz autenticação na API HubSoft."""
        try:
            auth_data = {
                "username": self.username,
                "password": self.password
            }

            response = await self._make_request(
                "POST",
                "/auth/login",
                data=auth_data,
                authenticated=False
            )

            token = response.get('access_token')
            if not token:
                raise HubSoftAPIError("No access token in response")

            # Armazena token
            expires_in = response.get('expires_in', 3600)
            await self.token_manager.store_token(token, expires_in)

            logger.info("Autenticação HubSoft realizada com sucesso")
            return token

        except Exception as e:
            logger.error(f"Erro na autenticação HubSoft: {e}")
            raise HubSoftAPIError(f"Authentication failed: {str(e)}")

    async def verify_client_by_cpf(
        self,
        cpf: str,
        include_contracts: bool = True
    ) -> Dict[str, Any]:
        """Verifica cliente no HubSoft por CPF."""
        try:
            params = {
                "cpf": cpf,
                "include_contracts": include_contracts
            }

            response = await self._make_request(
                "GET",
                "/clients/verify",
                params=params
            )

            logger.info(f"Cliente verificado: CPF={cpf[:3]}***{cpf[-2:]}")
            return response

        except Exception as e:
            logger.error(f"Erro ao verificar cliente: {e}")
            raise

    async def create_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cria ticket no HubSoft."""
        try:
            response = await self._make_request(
                "POST",
                "/tickets",
                data=ticket_data
            )

            ticket_id = response.get('id')
            logger.info(f"Ticket criado no HubSoft: {ticket_id}")
            return response

        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            raise

    async def update_ticket(
        self,
        hubsoft_ticket_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atualiza ticket no HubSoft."""
        try:
            response = await self._make_request(
                "PATCH",
                f"/tickets/{hubsoft_ticket_id}",
                data=updates
            )

            logger.info(f"Ticket atualizado no HubSoft: {hubsoft_ticket_id}")
            return response

        except Exception as e:
            logger.error(f"Erro ao atualizar ticket: {e}")
            raise

    async def get_ticket_status(
        self,
        hubsoft_ticket_id: str
    ) -> Dict[str, Any]:
        """Obtém status de ticket no HubSoft."""
        try:
            response = await self._make_request(
                "GET",
                f"/tickets/{hubsoft_ticket_id}/status"
            )

            return response

        except Exception as e:
            logger.error(f"Erro ao obter status do ticket: {e}")
            raise

    async def search_tickets_by_cpf(
        self,
        cpf: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Busca tickets por CPF do cliente."""
        try:
            params = {
                "cpf": cpf,
                "limit": limit
            }

            response = await self._make_request(
                "GET",
                "/tickets/search",
                params=params
            )

            tickets = response.get('tickets', [])
            logger.info(f"Encontrados {len(tickets)} tickets para CPF={cpf[:3]}***{cpf[-2:]}")
            return tickets

        except Exception as e:
            logger.error(f"Erro ao buscar tickets: {e}")
            raise

    async def get_client_contracts(
        self,
        cpf: str
    ) -> List[Dict[str, Any]]:
        """Obtém contratos do cliente."""
        try:
            params = {"cpf": cpf}

            response = await self._make_request(
                "GET",
                "/clients/contracts",
                params=params
            )

            contracts = response.get('contracts', [])
            logger.info(f"Encontrados {len(contracts)} contratos para CPF={cpf[:3]}***{cpf[-2:]}")
            return contracts

        except Exception as e:
            logger.error(f"Erro ao obter contratos: {e}")
            raise

    async def check_api_health(self) -> Dict[str, Any]:
        """Verifica saúde da API HubSoft."""
        try:
            start_time = datetime.now()

            response = await self._make_request(
                "GET",
                "/health",
                authenticated=False
            )

            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "timestamp": start_time.isoformat(),
                "details": response
            }

        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Obtém status do rate limiting."""
        return await self.rate_limiter.get_status()

    async def close(self) -> None:
        """Fecha recursos."""
        if self._session and not self._session.closed:
            await self._session.close()


class HubSoftCacheService(HubSoftCacheRepository):
    """Implementação do serviço de cache HubSoft."""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()

    async def get_cached_client_data(
        self,
        cpf: str
    ) -> Optional[Dict[str, Any]]:
        """Obtém dados de cliente do cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        return await self.cache_manager.get(cache_key)

    async def cache_client_data(
        self,
        cpf: str,
        client_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """Armazena dados de cliente no cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        await self.cache_manager.set(cache_key, client_data, ttl_seconds)

    async def get_cached_ticket_data(
        self,
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtém dados de ticket do cache."""
        cache_key = f"ticket_data:{ticket_id}"
        return await self.cache_manager.get(cache_key)

    async def cache_ticket_data(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any],
        ttl_seconds: int = 1800
    ) -> None:
        """Armazena dados de ticket no cache."""
        cache_key = f"ticket_data:{ticket_id}"
        await self.cache_manager.set(cache_key, ticket_data, ttl_seconds)

    async def invalidate_client_cache(
        self,
        cpf: str
    ) -> None:
        """Invalida cache de cliente."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        await self.cache_manager.delete(cache_key)

    async def invalidate_ticket_cache(
        self,
        ticket_id: str
    ) -> None:
        """Invalida cache de ticket."""
        cache_key = f"ticket_data:{ticket_id}"
        await self.cache_manager.delete(cache_key)

    async def clear_expired_cache(self) -> int:
        """Remove entradas expiradas do cache."""
        return await self.cache_manager.cleanup_expired()

    def _hash_cpf(self, cpf: str) -> str:
        """Gera hash do CPF para usar como chave de cache."""
        return hashlib.sha256(cpf.encode()).hexdigest()[:16]