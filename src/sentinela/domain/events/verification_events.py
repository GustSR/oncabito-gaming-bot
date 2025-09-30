"""
Domain Events relacionados à verificação de CPF.

Define os eventos que são disparados durante
o processo de verificação de CPF dos usuários.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent
from ..entities.cpf_verification import VerificationId


@dataclass(frozen=True)
class VerificationStarted(DomainEvent):
    """
    Evento disparado quando uma verificação de CPF é iniciada.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        verification_type: Tipo de verificação
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    verification_type: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class VerificationAttemptMade(DomainEvent):
    """
    Evento disparado quando uma tentativa de verificação é feita.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        attempt_number: Número da tentativa
        success: Se a tentativa foi bem-sucedida
        cpf_provided: CPF fornecido (mascarado)
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    attempt_number: int
    success: bool
    cpf_provided: Optional[str] = None
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class VerificationCompleted(DomainEvent):
    """
    Evento disparado quando uma verificação é completada com sucesso.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        verification_type: Tipo de verificação
        cpf_number: CPF verificado (mascarado)
        success: Se foi bem-sucedida
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    verification_type: str
    cpf_number: str
    success: bool
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class VerificationFailed(DomainEvent):
    """
    Evento disparado quando uma verificação falha.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        verification_type: Tipo de verificação
        reason: Motivo da falha
        attempt_count: Número de tentativas feitas
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    verification_type: str
    reason: str
    attempt_count: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class VerificationCancelled(DomainEvent):
    """
    Evento disparado quando uma verificação é cancelada.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        reason: Motivo do cancelamento
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    reason: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class VerificationExpired(DomainEvent):
    """
    Evento disparado quando uma verificação expira.

    Attributes:
        verification_id: ID da verificação
        user_id: ID do usuário
        username: Nome de usuário
        verification_type: Tipo de verificação
        expires_at: Timestamp de expiração
        occurred_at: Timestamp do evento
    """
    verification_id: VerificationId
    user_id: int
    username: str
    verification_type: str
    expires_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class CPFDuplicateDetected(DomainEvent):
    """
    Evento disparado quando um CPF duplicado é detectado.

    Attributes:
        cpf_number: CPF duplicado (mascarado)
        current_user_id: ID do usuário atual
        existing_user_id: ID do usuário que já possui o CPF
        current_username: Nome do usuário atual
        existing_username: Nome do usuário existente
        resolution_action: Ação tomada para resolver conflito
        occurred_at: Timestamp do evento
    """
    cpf_number: str  # Mascarado
    current_user_id: int
    existing_user_id: int
    current_username: str
    existing_username: str
    resolution_action: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class CPFRemapped(DomainEvent):
    """
    Evento disparado quando um CPF é remapeado para um novo usuário.

    Attributes:
        cpf_number: CPF remapeado (mascarado)
        old_user_id: ID do usuário anterior
        new_user_id: ID do novo usuário
        old_username: Nome do usuário anterior
        new_username: Nome do novo usuário
        reason: Motivo do remapeamento
        occurred_at: Timestamp do evento
    """
    cpf_number: str  # Mascarado
    old_user_id: int
    new_user_id: int
    old_username: str
    new_username: str
    reason: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()