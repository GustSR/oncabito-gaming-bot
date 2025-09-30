"""
Domain Events relacionados a tickets.

Define os eventos que são disparados quando
o estado dos tickets muda.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent
from ..value_objects.identifiers import TicketId, UserId, HubSoftId, Protocol


@dataclass(frozen=True)
class TicketCreated(DomainEvent):
    """
    Evento disparado quando um novo ticket é criado.

    Attributes:
        ticket_id: ID do ticket criado
        user_id: ID do usuário que criou
        username: Nome do usuário
        category: Categoria do problema
        affected_game: Jogo afetado
        problem_timing: Quando o problema começou
        description: Descrição do problema
        protocol: Protocolo de atendimento
        occurred_at: Timestamp do evento
    """
    ticket_id: TicketId
    user_id: int
    username: str
    category: str
    affected_game: str
    problem_timing: str
    description: str
    protocol: Protocol
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class TicketAssigned(DomainEvent):
    """
    Evento disparado quando um ticket é atribuído a um técnico.

    Attributes:
        ticket_id: ID do ticket
        technician: Nome do técnico
        status: Novo status do ticket
        occurred_at: Timestamp do evento
    """
    ticket_id: TicketId
    technician: str
    status: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class TicketStatusChanged(DomainEvent):
    """
    Evento disparado quando o status de um ticket muda.

    Attributes:
        ticket_id: ID do ticket
        user_id: ID do usuário dono do ticket
        old_status: Status anterior
        new_status: Novo status
        occurred_at: Timestamp do evento
    """
    ticket_id: TicketId
    user_id: int
    old_status: str
    new_status: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class TicketSyncedWithHubSoft(DomainEvent):
    """
    Evento disparado quando um ticket é sincronizado com o HubSoft.

    Attributes:
        ticket_id: ID do ticket local
        hubsoft_id: ID no sistema HubSoft
        sync_status: Status da sincronização
        occurred_at: Timestamp do evento
    """
    ticket_id: TicketId
    hubsoft_id: HubSoftId
    sync_status: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class TicketClosed(DomainEvent):
    """
    Evento disparado quando um ticket é fechado.

    Attributes:
        ticket_id: ID do ticket
        user_id: ID do usuário
        resolution_notes: Notas da resolução
        closed_by: Quem fechou o ticket
    """
    ticket_id: TicketId
    user_id: int
    resolution_notes: str
    closed_by: str


@dataclass(frozen=True)
class TicketReopened(DomainEvent):
    """
    Evento disparado quando um ticket é reaberto.

    Attributes:
        ticket_id: ID do ticket
        user_id: ID do usuário
        reason: Motivo da reabertura
        reopened_by: Quem reabriu o ticket
    """
    ticket_id: TicketId
    user_id: int
    reason: str
    reopened_by: str


@dataclass(frozen=True)
class TicketUrgencyElevated(DomainEvent):
    """
    Evento disparado quando a urgência de um ticket é elevada.

    Attributes:
        ticket_id: ID do ticket
        old_urgency: Urgência anterior
        new_urgency: Nova urgência
        reason: Motivo da elevação
    """
    ticket_id: TicketId
    old_urgency: str
    new_urgency: str
    reason: str


@dataclass(frozen=True)
class TechNotificationRequiredEvent(DomainEvent):
    """
    Evento disparado quando notificação técnica é necessária.

    Attributes:
        ticket_protocol: Protocolo do ticket relacionado
        priority: Prioridade da notificação
        message: Mensagem formatada para envio
        channel_id: ID do canal de destino
        created_at: Data/hora da criação
    """
    ticket_protocol: str
    priority: 'NotificationPriority'  # Forward reference
    message: str
    channel_id: int
    created_at: datetime