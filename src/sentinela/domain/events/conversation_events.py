"""
Domain Events relacionados a conversas de suporte.

Define os eventos que são disparados durante
o fluxo de conversas de suporte.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent
from ..value_objects.identifiers import ConversationId, TicketId


@dataclass(frozen=True)
class ConversationStarted(DomainEvent):
    """
    Evento disparado quando uma nova conversa de suporte é iniciada.

    Attributes:
        conversation_id: ID da conversa
        user_id: ID do usuário
        username: Nome de usuário
        started_at: Data/hora de início
        occurred_at: Timestamp do evento
    """
    conversation_id: ConversationId
    user_id: int
    username: str
    started_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConversationCompleted(DomainEvent):
    """
    Evento disparado quando uma conversa é completada com sucesso.

    Attributes:
        conversation_id: ID da conversa
        user_id: ID do usuário
        username: Nome de usuário
        ticket_id: ID do ticket criado
        started_at: Data/hora de início
        completed_at: Data/hora de conclusão
        occurred_at: Timestamp do evento
    """
    conversation_id: ConversationId
    user_id: int
    username: str
    ticket_id: TicketId
    started_at: datetime
    completed_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConversationCancelled(DomainEvent):
    """
    Evento disparado quando uma conversa é cancelada.

    Attributes:
        conversation_id: ID da conversa
        user_id: ID do usuário
        username: Nome de usuário
        reason: Motivo do cancelamento
        step: Em qual passo foi cancelada
        started_at: Data/hora de início
        cancelled_at: Data/hora do cancelamento
        occurred_at: Timestamp do evento
    """
    conversation_id: ConversationId
    user_id: int
    username: str
    reason: str
    step: str
    started_at: datetime
    cancelled_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConversationStepCompleted(DomainEvent):
    """
    Evento disparado quando um passo da conversa é completado.

    Attributes:
        conversation_id: ID da conversa
        user_id: ID do usuário
        username: Nome de usuário
        step: Passo que foi completado
        next_step: Próximo passo
        data: Dados coletados no passo
    """
    conversation_id: ConversationId
    user_id: int
    username: str
    step: str
    next_step: Optional[str]
    data: dict


@dataclass(frozen=True)
class ConversationTimedOut(DomainEvent):
    """
    Evento disparado quando uma conversa expira por timeout.

    Attributes:
        conversation_id: ID da conversa
        user_id: ID do usuário
        username: Nome de usuário
        last_step: Último passo ativo
        timeout_minutes: Tempo de timeout em minutos
        started_at: Data/hora de início
        timed_out_at: Data/hora do timeout
    """
    conversation_id: ConversationId
    user_id: int
    username: str
    last_step: str
    timeout_minutes: int
    started_at: datetime
    timed_out_at: datetime