"""
Domain Events relacionados ao grupo.

Define os eventos que são disparados quando
o estado do grupo muda.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent


@dataclass(frozen=True)
class TopicDiscoveredEvent(DomainEvent):
    """
    Evento disparado quando novo tópico é descoberto.

    Attributes:
        topic_id: ID do tópico no Telegram
        topic_name: Nome do tópico
        category: Categoria do tópico
        discovered_at: Data/hora da descoberta
    """
    topic_id: int
    topic_name: str
    category: str
    discovered_at: datetime


@dataclass(frozen=True)
class TopicActivityUpdatedEvent(DomainEvent):
    """
    Evento disparado quando atividade de tópico é atualizada.

    Attributes:
        topic_id: ID do tópico
        message_id: ID da mensagem
        updated_at: Data/hora da atualização
    """
    topic_id: int
    message_id: int
    updated_at: datetime


@dataclass(frozen=True)
class TopicNameChangedEvent(DomainEvent):
    """
    Evento disparado quando nome de tópico muda.

    Attributes:
        topic_id: ID do tópico
        old_name: Nome anterior
        new_name: Novo nome
        changed_at: Data/hora da mudança
    """
    topic_id: int
    old_name: str
    new_name: str
    changed_at: datetime


@dataclass(frozen=True)
class TopicMarkedInactiveEvent(DomainEvent):
    """
    Evento disparado quando tópico é marcado como inativo.

    Attributes:
        topic_id: ID do tópico
        reason: Motivo da inativação
        marked_at: Data/hora da marcação
    """
    topic_id: int
    reason: Optional[str]
    marked_at: datetime


@dataclass(frozen=True)
class MemberJoinedGroupEvent(DomainEvent):
    """
    Evento disparado quando membro entra no grupo.

    Attributes:
        user_id: ID do usuário
        username: Nome do usuário
        joined_at: Data/hora de entrada
    """
    user_id: int
    username: str
    joined_at: datetime


@dataclass(frozen=True)
class MemberLeftGroupEvent(DomainEvent):
    """
    Evento disparado quando membro sai do grupo.

    Attributes:
        user_id: ID do usuário
        username: Nome do usuário
        left_at: Data/hora de saída
    """
    user_id: int
    username: str
    left_at: datetime
