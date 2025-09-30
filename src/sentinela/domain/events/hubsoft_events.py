"""
Domain Events relacionados à integração com HubSoft.

Define os eventos que são disparados durante
operações de integração com o sistema HubSoft.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from ..entities.base import DomainEvent
from ..entities.hubsoft_integration import IntegrationId


@dataclass(frozen=True)
class IntegrationScheduled(DomainEvent):
    """
    Evento disparado quando uma integração é agendada.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        priority: Prioridade da integração
        scheduled_at: Quando foi agendada para execução
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    priority: str
    scheduled_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationStarted(DomainEvent):
    """
    Evento disparado quando uma integração é iniciada.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        priority: Prioridade da integração
        attempt_number: Número da tentativa
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    priority: str
    attempt_number: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationAttemptMade(DomainEvent):
    """
    Evento disparado quando uma tentativa de integração é feita.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        attempt_number: Número da tentativa
        success: Se a tentativa foi bem-sucedida
        error_message: Mensagem de erro (se aplicável)
        duration_ms: Duração em milissegundos
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    attempt_number: int
    success: bool
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationCompleted(DomainEvent):
    """
    Evento disparado quando uma integração é completada com sucesso.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        priority: Prioridade da integração
        success: Se foi bem-sucedida
        total_attempts: Total de tentativas feitas
        duration_seconds: Duração total em segundos
        response_data: Dados de resposta (resumo)
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    priority: str
    success: bool
    total_attempts: int
    duration_seconds: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationFailed(DomainEvent):
    """
    Evento disparado quando uma integração falha definitivamente.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        priority: Prioridade da integração
        total_attempts: Total de tentativas feitas
        final_error: Erro final que causou a falha
        error_details: Detalhes técnicos do erro
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    priority: str
    total_attempts: int
    final_error: str
    error_details: Optional[Dict[str, Any]] = None
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationRetryScheduled(DomainEvent):
    """
    Evento disparado quando um retry é agendado após falha.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        attempt_number: Número da tentativa que falhou
        retry_delay_seconds: Delay até próximo retry em segundos
        error_message: Erro que motivou o retry
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    attempt_number: int
    retry_delay_seconds: int
    error_message: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationCancelled(DomainEvent):
    """
    Evento disparado quando uma integração é cancelada.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        reason: Motivo do cancelamento
        attempts_made: Tentativas feitas antes do cancelamento
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    reason: str
    attempts_made: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class IntegrationPriorityChanged(DomainEvent):
    """
    Evento disparado quando a prioridade de uma integração muda.

    Attributes:
        integration_id: ID da integração
        integration_type: Tipo de integração
        old_priority: Prioridade anterior
        new_priority: Nova prioridade
        reason: Motivo da mudança
        occurred_at: Timestamp do evento
    """
    integration_id: IntegrationId
    integration_type: str
    old_priority: str
    new_priority: str
    reason: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class HubSoftTicketSynced(DomainEvent):
    """
    Evento disparado quando um ticket é sincronizado com HubSoft.

    Attributes:
        ticket_id: ID do ticket local
        hubsoft_ticket_id: ID do ticket no HubSoft
        sync_type: Tipo de sincronização (create, update, status_change)
        sync_data: Dados sincronizados
        occurred_at: Timestamp do evento
    """
    ticket_id: str
    hubsoft_ticket_id: str
    sync_type: str
    sync_data: Dict[str, Any]
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class HubSoftUserDataFetched(DomainEvent):
    """
    Evento disparado quando dados de usuário são buscados no HubSoft.

    Attributes:
        user_id: ID do usuário local
        cpf: CPF usado na busca (mascarado)
        client_data: Dados do cliente retornados
        cache_duration: Duração do cache em segundos
        occurred_at: Timestamp do evento
    """
    user_id: int
    cpf: str  # Mascarado
    client_data: Dict[str, Any]
    cache_duration: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class HubSoftRateLimitHit(DomainEvent):
    """
    Evento disparado quando rate limit do HubSoft é atingido.

    Attributes:
        integration_type: Tipo de integração afetada
        current_rate: Taxa atual de requests
        limit_threshold: Limite configurado
        reset_time: Quando o limite reseta
        affected_operations: Operações que foram afetadas
        occurred_at: Timestamp do evento
    """
    integration_type: str
    current_rate: int
    limit_threshold: int
    reset_time: datetime
    affected_operations: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class HubSoftConnectionRestored(DomainEvent):
    """
    Evento disparado quando conexão com HubSoft é restaurada.

    Attributes:
        downtime_duration: Duração da indisponibilidade em segundos
        pending_operations: Operações pendentes para reprocessar
        connection_quality: Qualidade da conexão (good, fair, poor)
        occurred_at: Timestamp do evento
    """
    downtime_duration: int
    pending_operations: int
    connection_quality: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class HubSoftBulkSyncCompleted(DomainEvent):
    """
    Evento disparado quando sincronização em lote é completada.

    Attributes:
        sync_batch_id: ID do lote de sincronização
        sync_type: Tipo de sincronização em lote
        total_items: Total de itens no lote
        successful_items: Itens sincronizados com sucesso
        failed_items: Itens que falharam
        duration_seconds: Duração total da sincronização
        occurred_at: Timestamp do evento
    """
    sync_batch_id: str
    sync_type: str
    total_items: int
    successful_items: int
    failed_items: int
    duration_seconds: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()