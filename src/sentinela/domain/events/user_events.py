"""
Domain Events relacionados a usuários.

Define os eventos que são disparados quando
o estado dos usuários muda.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent
from ..value_objects.identifiers import UserId


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """
    Evento disparado quando um novo usuário se registra.

    Attributes:
        user_id: ID do usuário registrado
        username: Nome de usuário
        registration_date: Data/hora do registro
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    registration_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class UserBanned(DomainEvent):
    """
    Evento disparado quando um usuário é banido.

    Attributes:
        user_id: ID do usuário banido
        username: Nome de usuário
        reason: Motivo do banimento
        banned_by: Quem aplicou o banimento
        ban_date: Data/hora do banimento
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    reason: str
    banned_by: str
    ban_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class UserUnbanned(DomainEvent):
    """
    Evento disparado quando um usuário é desbanido.

    Attributes:
        user_id: ID do usuário desbanido
        username: Nome de usuário
        unbanned_by: Quem removeu o banimento
        unban_date: Data/hora da remoção do banimento
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    unbanned_by: str
    unban_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class CPFValidated(DomainEvent):
    """
    Evento disparado quando um CPF é validado.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        cpf_number: Número do CPF
        is_valid: Se o CPF é válido
        validation_date: Data/hora da validação
    """
    user_id: int
    username: str
    cpf_number: str
    is_valid: bool
    validation_date: Optional[datetime] = None

    def __post_init__(self):
        if self.validation_date is None:
            object.__setattr__(self, 'validation_date', datetime.now())


@dataclass(frozen=True)
class UserProfileUpdated(DomainEvent):
    """
    Evento disparado quando o perfil de um usuário é atualizado.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        updated_fields: Campos que foram atualizados
        updated_by: Quem fez a atualização
    """
    user_id: int
    username: str
    updated_fields: dict
    updated_by: str


@dataclass(frozen=True)
class UserLastSeenUpdated(DomainEvent):
    """
    Evento disparado quando a última atividade do usuário é atualizada.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        last_seen: Última atividade registrada
        activity_type: Tipo de atividade (message, command, etc.)
    """
    user_id: int
    username: str
    last_seen: datetime
    activity_type: str