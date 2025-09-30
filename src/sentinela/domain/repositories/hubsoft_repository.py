"""
HubSoft Integration Repository.

Define interface para persistência e recuperação de
integrações com HubSoft, incluindo busca de dados externos.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..entities.hubsoft_integration import (
    HubSoftIntegrationRequest,
    IntegrationId,
    IntegrationType,
    IntegrationStatus
)


class HubSoftIntegrationRepository(ABC):
    """
    Repositório para operações de integração com HubSoft.

    Gerencia a persistência de solicitações de integração,
    incluindo busca e atualização de status.
    """

    @abstractmethod
    async def save(self, integration: HubSoftIntegrationRequest) -> None:
        """
        Salva uma solicitação de integração.

        Args:
            integration: Solicitação de integração a ser salva
        """
        pass

    @abstractmethod
    async def find_by_id(self, integration_id: IntegrationId) -> Optional[HubSoftIntegrationRequest]:
        """
        Busca integração por ID.

        Args:
            integration_id: ID da integração

        Returns:
            Integração encontrada ou None
        """
        pass

    @abstractmethod
    async def find_pending_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        limit: int = 50
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações pendentes.

        Args:
            integration_type: Tipo de integração (None = todos)
            limit: Limite de resultados

        Returns:
            Lista de integrações pendentes
        """
        pass

    @abstractmethod
    async def find_scheduled_integrations(
        self,
        until: datetime,
        limit: int = 50
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações agendadas até uma data.

        Args:
            until: Data limite
            limit: Limite de resultados

        Returns:
            Lista de integrações agendadas
        """
        pass

    @abstractmethod
    async def find_active_integrations(
        self,
        integration_type: Optional[IntegrationType] = None
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações ativas (em progresso).

        Args:
            integration_type: Tipo de integração (None = todos)

        Returns:
            Lista de integrações ativas
        """
        pass

    @abstractmethod
    async def find_failed_integrations(
        self,
        integration_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações falhadas.

        Args:
            integration_type: Tipo de integração (None = todos)
            since: Data de início da busca
            limit: Limite de resultados

        Returns:
            Lista de integrações falhadas
        """
        pass

    @abstractmethod
    async def find_completed_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações completadas.

        Args:
            integration_type: Tipo de integração (None = todos)
            since: Data de início da busca
            limit: Limite de resultados

        Returns:
            Lista de integrações completadas
        """
        pass

    @abstractmethod
    async def find_by_metadata(
        self,
        metadata_key: str,
        metadata_value: Any,
        status: Optional[IntegrationStatus] = None
    ) -> List[HubSoftIntegrationRequest]:
        """
        Busca integrações por metadados.

        Args:
            metadata_key: Chave dos metadados
            metadata_value: Valor dos metadados
            status: Status das integrações (None = todos)

        Returns:
            Lista de integrações encontradas
        """
        pass

    @abstractmethod
    async def count_integrations_by_status(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Conta integrações por status.

        Args:
            since: Data de início da contagem

        Returns:
            Dicionário com contagem por status
        """
        pass

    @abstractmethod
    async def cleanup_completed_integrations(
        self,
        older_than: datetime,
        batch_size: int = 100
    ) -> int:
        """
        Remove integrações completadas antigas.

        Args:
            older_than: Data limite
            batch_size: Tamanho do lote para remoção

        Returns:
            Número de integrações removidas
        """
        pass

    @abstractmethod
    async def get_integration_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        integration_type: Optional[IntegrationType] = None
    ) -> Dict[str, Any]:
        """
        Obtém métricas de integração.

        Args:
            start_date: Data de início
            end_date: Data de fim
            integration_type: Tipo de integração (None = todos)

        Returns:
            Dicionário com métricas
        """
        pass


class HubSoftAPIRepository(ABC):
    """
    Repositório para comunicação com a API do HubSoft.

    Abstrai operações de comunicação com o sistema externo,
    incluindo autenticação, rate limiting e tratamento de erros.
    """

    @abstractmethod
    async def verify_client_by_cpf(
        self,
        cpf: str,
        include_contracts: bool = True
    ) -> Dict[str, Any]:
        """
        Verifica cliente no HubSoft por CPF.

        Args:
            cpf: CPF do cliente
            include_contracts: Incluir dados de contratos

        Returns:
            Dados do cliente

        Raises:
            HubSoftAPIError: Erro na comunicação com API
        """
        pass

    @abstractmethod
    async def create_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria ticket no HubSoft.

        Args:
            ticket_data: Dados do ticket

        Returns:
            Dados do ticket criado

        Raises:
            HubSoftAPIError: Erro na criação do ticket
        """
        pass

    @abstractmethod
    async def update_ticket(
        self,
        hubsoft_ticket_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atualiza ticket no HubSoft.

        Args:
            hubsoft_ticket_id: ID do ticket no HubSoft
            updates: Dados para atualização

        Returns:
            Dados do ticket atualizado

        Raises:
            HubSoftAPIError: Erro na atualização
        """
        pass

    @abstractmethod
    async def get_ticket_status(
        self,
        hubsoft_ticket_id: str
    ) -> Dict[str, Any]:
        """
        Obtém status de ticket no HubSoft.

        Args:
            hubsoft_ticket_id: ID do ticket no HubSoft

        Returns:
            Status do ticket

        Raises:
            HubSoftAPIError: Erro na consulta
        """
        pass

    @abstractmethod
    async def search_tickets_by_cpf(
        self,
        cpf: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Busca tickets por CPF do cliente.

        Args:
            cpf: CPF do cliente
            limit: Limite de resultados

        Returns:
            Lista de tickets encontrados

        Raises:
            HubSoftAPIError: Erro na busca
        """
        pass

    @abstractmethod
    async def get_client_contracts(
        self,
        cpf: str
    ) -> List[Dict[str, Any]]:
        """
        Obtém contratos do cliente.

        Args:
            cpf: CPF do cliente

        Returns:
            Lista de contratos

        Raises:
            HubSoftAPIError: Erro na consulta
        """
        pass

    @abstractmethod
    async def check_api_health(self) -> Dict[str, Any]:
        """
        Verifica saúde da API HubSoft.

        Returns:
            Status da API

        Raises:
            HubSoftAPIError: Erro na verificação
        """
        pass

    @abstractmethod
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Obtém status do rate limiting.

        Returns:
            Status do rate limiting
        """
        pass


class HubSoftCacheRepository(ABC):
    """
    Repositório para cache de dados do HubSoft.

    Gerencia cache de dados obtidos da API para
    melhorar performance e reduzir carga na API externa.
    """

    @abstractmethod
    async def get_cached_client_data(
        self,
        cpf: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém dados de cliente do cache.

        Args:
            cpf: CPF do cliente

        Returns:
            Dados do cliente ou None se não encontrado
        """
        pass

    @abstractmethod
    async def cache_client_data(
        self,
        cpf: str,
        client_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """
        Armazena dados de cliente no cache.

        Args:
            cpf: CPF do cliente
            client_data: Dados do cliente
            ttl_seconds: Tempo de vida do cache em segundos
        """
        pass

    @abstractmethod
    async def get_cached_ticket_data(
        self,
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém dados de ticket do cache.

        Args:
            ticket_id: ID do ticket

        Returns:
            Dados do ticket ou None se não encontrado
        """
        pass

    @abstractmethod
    async def cache_ticket_data(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any],
        ttl_seconds: int = 1800
    ) -> None:
        """
        Armazena dados de ticket no cache.

        Args:
            ticket_id: ID do ticket
            ticket_data: Dados do ticket
            ttl_seconds: Tempo de vida do cache em segundos
        """
        pass

    @abstractmethod
    async def invalidate_client_cache(
        self,
        cpf: str
    ) -> None:
        """
        Invalida cache de cliente.

        Args:
            cpf: CPF do cliente
        """
        pass

    @abstractmethod
    async def invalidate_ticket_cache(
        self,
        ticket_id: str
    ) -> None:
        """
        Invalida cache de ticket.

        Args:
            ticket_id: ID do ticket
        """
        pass

    @abstractmethod
    async def clear_expired_cache(self) -> int:
        """
        Remove entradas expiradas do cache.

        Returns:
            Número de entradas removidas
        """
        pass


class HubSoftAPIError(Exception):
    """Erro de comunicação com API HubSoft."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def is_retryable(self) -> bool:
        """Verifica se erro pode ser retentado."""
        if not self.status_code:
            return True  # Erros de conexão são retentáveis

        # Status codes retentáveis
        retryable_codes = {429, 500, 502, 503, 504}
        return self.status_code in retryable_codes

    def is_rate_limit(self) -> bool:
        """Verifica se erro é de rate limiting."""
        return self.status_code == 429 or self.error_code == "rate_limit_exceeded"