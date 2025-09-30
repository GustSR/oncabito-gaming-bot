"""
Mock HubSoft API Service.

Implementação mock para testes e desenvolvimento,
sem dependências externas.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from ...domain.repositories.hubsoft_repository import (
    HubSoftAPIRepository,
    HubSoftCacheRepository,
    HubSoftAPIError
)

logger = logging.getLogger(__name__)


class MockHubSoftAPIService(HubSoftAPIRepository):
    """Implementação mock do serviço de API HubSoft."""

    def __init__(
        self,
        base_url: str = None,
        username: str = None,
        password: str = None,
        rate_limiter=None,
        token_manager=None,
        timeout_seconds: int = 30,
        simulate_errors: bool = False,
        response_delay: float = 0.1
    ):
        # Mock service ignores real parameters but accepts them for compatibility
        self.simulate_errors = simulate_errors
        self.response_delay = response_delay
        self._request_count = 0

    async def verify_client_by_cpf(
        self,
        cpf: str,
        include_contracts: bool = True
    ) -> Dict[str, Any]:
        """Mock de verificação de cliente."""
        self._request_count += 1

        if self.simulate_errors and self._request_count % 5 == 0:
            raise HubSoftAPIError("Simulated API error", status_code=500)

        # Simula delay
        import asyncio
        await asyncio.sleep(self.response_delay)

        # Dados mock baseados no CPF
        client_data = {
            "cpf": cpf,
            "name": f"Cliente {cpf[:3]}***{cpf[-2:]}",
            "email": f"cliente{cpf[-4:]}@email.com",
            "phone": f"(11) 9{cpf[-4:]}-{cpf[-4:]}",
            "status": "active",
            "verified": True
        }

        if include_contracts:
            client_data["contracts"] = [
                {
                    "id": f"CTR{cpf[-3:]}001",
                    "status": "active",
                    "service": "Internet",
                    "plan": "100MB"
                },
                {
                    "id": f"CTR{cpf[-3:]}002",
                    "status": "active",
                    "service": "TV",
                    "plan": "Premium"
                }
            ]

        logger.info(f"Mock: Cliente verificado - CPF={cpf[:3]}***{cpf[-2:]}")
        return client_data

    async def create_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock de criação de ticket."""
        self._request_count += 1

        if self.simulate_errors and self._request_count % 8 == 0:
            raise HubSoftAPIError("Simulated ticket creation error", status_code=422)

        import asyncio
        await asyncio.sleep(self.response_delay)

        # Gera ID mock
        hubsoft_id = f"HST_{int(datetime.now().timestamp())}"

        response = {
            "id": hubsoft_id,
            "protocol": hubsoft_id,
            "status": "created",
            "title": ticket_data.get("title", "Ticket"),
            "description": ticket_data.get("description", ""),
            "priority": ticket_data.get("priority", "normal"),
            "created_at": datetime.now().isoformat(),
            "estimated_resolution": "24h",
            "assigned_technician": "TecnicoGaming01"
        }

        logger.info(f"Mock: Ticket criado - ID={hubsoft_id}")
        return response

    async def update_ticket(
        self,
        hubsoft_ticket_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock de atualização de ticket."""
        self._request_count += 1

        import asyncio
        await asyncio.sleep(self.response_delay)

        response = {
            "id": hubsoft_ticket_id,
            "status": "updated",
            "updates_applied": list(updates.keys()),
            "updated_at": datetime.now().isoformat(),
            "next_action": "Aguardando retorno do cliente"
        }

        logger.info(f"Mock: Ticket atualizado - ID={hubsoft_ticket_id}")
        return response

    async def get_ticket_status(
        self,
        hubsoft_ticket_id: str
    ) -> Dict[str, Any]:
        """Mock de status de ticket."""
        import asyncio
        await asyncio.sleep(self.response_delay)

        return {
            "id": hubsoft_ticket_id,
            "status": "in_progress",
            "progress": "Análise inicial concluída",
            "last_update": datetime.now().isoformat(),
            "next_step": "Teste de conectividade"
        }

    async def search_tickets_by_cpf(
        self,
        cpf: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Mock de busca de tickets."""
        import asyncio
        await asyncio.sleep(self.response_delay)

        # Simula alguns tickets
        tickets = []
        for i in range(min(3, limit)):
            tickets.append({
                "id": f"HST_{cpf[-3:]}_{i:03d}",
                "status": ["open", "in_progress", "closed"][i % 3],
                "title": f"Ticket {i+1} - Suporte técnico",
                "created_at": datetime.now().isoformat(),
                "priority": "normal"
            })

        logger.info(f"Mock: Encontrados {len(tickets)} tickets para CPF={cpf[:3]}***{cpf[-2:]}")
        return tickets

    async def get_client_contracts(
        self,
        cpf: str
    ) -> List[Dict[str, Any]]:
        """Mock de contratos do cliente."""
        import asyncio
        await asyncio.sleep(self.response_delay)

        contracts = [
            {
                "id": f"CTR{cpf[-3:]}001",
                "status": "active",
                "service": "Internet",
                "plan": "100MB Fibra",
                "monthly_fee": 89.90,
                "installation_date": "2023-01-15"
            },
            {
                "id": f"CTR{cpf[-3:]}002",
                "status": "active",
                "service": "TV",
                "plan": "Premium 200 canais",
                "monthly_fee": 149.90,
                "installation_date": "2023-01-15"
            }
        ]

        logger.info(f"Mock: {len(contracts)} contratos para CPF={cpf[:3]}***{cpf[-2:]}")
        return contracts

    async def check_api_health(self) -> Dict[str, Any]:
        """Mock de health check."""
        import asyncio
        await asyncio.sleep(self.response_delay)

        return {
            "status": "healthy",
            "response_time_ms": int(self.response_delay * 1000),
            "version": "1.0.0-mock",
            "timestamp": datetime.now().isoformat(),
            "requests_processed": self._request_count,
            "uptime": "99.9%"
        }

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Mock de rate limit status."""
        return {
            "requests_remaining": 950,
            "reset_time": datetime.now().isoformat(),
            "limit": 1000,
            "current_usage": self._request_count
        }


    async def close(self) -> None:
        """Fecha conexões e limpa recursos."""
        logger.debug("Mock API: Conexões fechadas")
        pass


class MockHubSoftCacheService(HubSoftCacheRepository):
    """Implementação mock do serviço de cache HubSoft."""

    def __init__(self, cache_manager=None):
        # Mock service ignores cache_manager but accepts it for compatibility
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get_cached_client_data(
        self,
        cpf: str
    ) -> Optional[Dict[str, Any]]:
        """Mock de dados de cliente do cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        cache_entry = self._cache.get(cache_key)

        if cache_entry and cache_entry["expires_at"] > datetime.now():
            logger.debug(f"Mock: Cache hit para CPF={cpf[:3]}***{cpf[-2:]}")
            return cache_entry["data"]

        logger.debug(f"Mock: Cache miss para CPF={cpf[:3]}***{cpf[-2:]}")
        return None

    async def cache_client_data(
        self,
        cpf: str,
        client_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """Mock de armazenamento no cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        expires_at = datetime.now().timestamp() + ttl_seconds

        self._cache[cache_key] = {
            "data": client_data,
            "expires_at": datetime.fromtimestamp(expires_at),
            "cached_at": datetime.now()
        }

        logger.debug(f"Mock: Dados cacheados para CPF={cpf[:3]}***{cpf[-2:]}")

    async def get_cached_ticket_data(
        self,
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Mock de dados de ticket do cache."""
        cache_key = f"ticket_data:{ticket_id}"
        cache_entry = self._cache.get(cache_key)

        if cache_entry and cache_entry["expires_at"] > datetime.now():
            return cache_entry["data"]

        return None

    async def cache_ticket_data(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any],
        ttl_seconds: int = 1800
    ) -> None:
        """Mock de armazenamento de ticket no cache."""
        cache_key = f"ticket_data:{ticket_id}"
        expires_at = datetime.now().timestamp() + ttl_seconds

        self._cache[cache_key] = {
            "data": ticket_data,
            "expires_at": datetime.fromtimestamp(expires_at),
            "cached_at": datetime.now()
        }

    async def invalidate_client_cache(
        self,
        cpf: str
    ) -> None:
        """Mock de invalidação de cache de cliente."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Mock: Cache invalidado para CPF={cpf[:3]}***{cpf[-2:]}")

    async def invalidate_ticket_cache(
        self,
        ticket_id: str
    ) -> None:
        """Mock de invalidação de cache de ticket."""
        cache_key = f"ticket_data:{ticket_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]

    async def clear_expired_cache(self) -> int:
        """Mock de limpeza de cache expirado."""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry["expires_at"] <= now
        ]

        for key in expired_keys:
            del self._cache[key]

        logger.debug(f"Mock: {len(expired_keys)} entradas expiradas removidas")
        return len(expired_keys)

    def _hash_cpf(self, cpf: str) -> str:
        """Gera hash simples do CPF."""
        import hashlib
        return hashlib.md5(cpf.encode()).hexdigest()[:16]

    async def close(self) -> None:
        """Fecha conexões e limpa recursos."""
        logger.debug("Mock: Conexões fechadas")
        pass