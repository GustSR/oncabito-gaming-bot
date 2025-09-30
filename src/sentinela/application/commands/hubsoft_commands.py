"""
HubSoft Integration Commands.

Define comandos para operações de integração com HubSoft,
incluindo sincronização de dados, verificação de usuários e tickets.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import Command


@dataclass(frozen=True)
class ScheduleHubSoftIntegrationCommand(Command):
    """
    Comando para agendar uma integração com HubSoft.

    Attributes:
        integration_type: Tipo de integração (ticket_sync, user_verification, etc.)
        priority: Prioridade da integração
        payload: Dados da integração
        scheduled_at: Quando executar (None = imediato)
        metadata: Metadados adicionais
        max_retries: Máximo de tentativas
        timeout_seconds: Timeout da operação
    """
    integration_type: str
    priority: str = "normal"
    payload: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass(frozen=True)
class SyncTicketToHubSoftCommand(Command):
    """
    Comando para sincronizar ticket com HubSoft.

    Attributes:
        ticket_id: ID do ticket local
        sync_type: Tipo de sincronização (create, update, status_change)
        hubsoft_ticket_id: ID do ticket no HubSoft (para updates)
        priority: Prioridade da sincronização
        force_sync: Forçar sincronização mesmo se já sincronizado
    """
    ticket_id: str
    sync_type: str  # create, update, status_change
    hubsoft_ticket_id: Optional[str] = None
    priority: str = "normal"
    force_sync: bool = False


@dataclass(frozen=True)
class VerifyUserInHubSoftCommand(Command):
    """
    Comando para verificar usuário no HubSoft.

    Attributes:
        user_id: ID do usuário local
        cpf: CPF para verificação
        cache_duration: Duração do cache em segundos
        force_refresh: Forçar atualização do cache
        include_contracts: Incluir dados de contratos
    """
    user_id: int
    cpf: str
    cache_duration: int = 3600
    force_refresh: bool = False
    include_contracts: bool = True


@dataclass(frozen=True)
class FetchClientDataFromHubSoftCommand(Command):
    """
    Comando para buscar dados de cliente no HubSoft.

    Attributes:
        cpf: CPF do cliente
        include_tickets: Incluir tickets existentes
        include_contracts: Incluir dados de contratos
        include_billing: Incluir dados de faturamento
        cache_duration: Duração do cache em segundos
    """
    cpf: str
    include_tickets: bool = True
    include_contracts: bool = True
    include_billing: bool = False
    cache_duration: int = 3600


@dataclass(frozen=True)
class UpdateTicketStatusInHubSoftCommand(Command):
    """
    Comando para atualizar status de ticket no HubSoft.

    Attributes:
        ticket_id: ID do ticket local
        hubsoft_ticket_id: ID do ticket no HubSoft
        new_status: Novo status do ticket
        technician_notes: Notas do técnico
        priority: Prioridade da atualização
    """
    ticket_id: str
    hubsoft_ticket_id: str
    new_status: str
    technician_notes: Optional[str] = None
    priority: str = "normal"


@dataclass(frozen=True)
class BulkSyncTicketsToHubSoftCommand(Command):
    """
    Comando para sincronização em lote de tickets.

    Attributes:
        ticket_ids: Lista de IDs de tickets
        sync_type: Tipo de sincronização
        batch_size: Tamanho do lote
        priority: Prioridade da operação
        delay_between_batches: Delay entre lotes em segundos
    """
    ticket_ids: List[str]
    sync_type: str
    batch_size: int = 10
    priority: str = "normal"
    delay_between_batches: int = 5


@dataclass(frozen=True)
class RetryFailedIntegrationsCommand(Command):
    """
    Comando para retentar integrações falhadas.

    Attributes:
        integration_type: Tipo de integração (None = todas)
        max_age_hours: Idade máxima das integrações em horas
        limit: Limite de integrações para retentar
        force_retry: Forçar retry mesmo se excedeu tentativas
    """
    integration_type: Optional[str] = None
    max_age_hours: int = 24
    limit: int = 50
    force_retry: bool = False


@dataclass(frozen=True)
class CancelHubSoftIntegrationCommand(Command):
    """
    Comando para cancelar integração pendente.

    Attributes:
        integration_id: ID da integração
        reason: Motivo do cancelamento
        notify_admin: Notificar administradores
    """
    integration_id: str
    reason: str = "Cancelado pelo usuário"
    notify_admin: bool = False


@dataclass(frozen=True)
class UpdateIntegrationPriorityCommand(Command):
    """
    Comando para alterar prioridade de integração.

    Attributes:
        integration_id: ID da integração
        new_priority: Nova prioridade
        reason: Motivo da alteração
    """
    integration_id: str
    new_priority: str
    reason: str


@dataclass(frozen=True)
class GetHubSoftIntegrationStatusCommand(Command):
    """
    Comando para obter status de integração.

    Attributes:
        integration_id: ID da integração (None = todas ativas)
        include_attempts: Incluir histórico de tentativas
        include_payload: Incluir dados da integração
    """
    integration_id: Optional[str] = None
    include_attempts: bool = False
    include_payload: bool = False


@dataclass(frozen=True)
class CleanupCompletedIntegrationsCommand(Command):
    """
    Comando para limpeza de integrações completadas.

    Attributes:
        max_age_days: Idade máxima em dias
        keep_failed: Manter integrações falhadas
        batch_size: Tamanho do lote para limpeza
    """
    max_age_days: int = 7
    keep_failed: bool = True
    batch_size: int = 100


@dataclass(frozen=True)
class ConfigureHubSoftRateLimitCommand(Command):
    """
    Comando para configurar rate limiting.

    Attributes:
        integration_type: Tipo de integração
        requests_per_minute: Requests por minuto
        burst_limit: Limite de burst
        enabled: Habilitar rate limiting
    """
    integration_type: str
    requests_per_minute: int
    burst_limit: int
    enabled: bool = True


@dataclass(frozen=True)
class GenerateHubSoftIntegrationReportCommand(Command):
    """
    Comando para gerar relatório de integrações.

    Attributes:
        start_date: Data de início
        end_date: Data de fim
        integration_types: Tipos de integração (None = todos)
        include_failed: Incluir integrações falhadas
        include_metrics: Incluir métricas de performance
        format: Formato do relatório (json, csv)
    """
    start_date: datetime
    end_date: datetime
    integration_types: Optional[List[str]] = None
    include_failed: bool = True
    include_metrics: bool = True
    format: str = "json"