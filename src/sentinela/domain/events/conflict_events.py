"""
Domain Events relacionados a conflitos de CPF duplicado.

Define os eventos que são disparados durante o processo
de detecção e resolução de conflitos de duplicata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from ..entities.base import DomainEvent


@dataclass(frozen=True)
class ConflictDetectedEvent(DomainEvent):
    """
    Evento disparado quando um conflito de CPF duplicado é detectado.

    Attributes:
        aggregate_id: ID do conflito
        conflict_id: ID do conflito
        cpf_hash: Hash do CPF duplicado
        user_ids: IDs dos usuários envolvidos
        notified_user_id: ID do usuário que será notificado
        expires_at: Data de expiração do conflito
        occurred_at: Timestamp do evento
    """
    conflict_id: str
    cpf_hash: str
    user_ids: List[int]
    notified_user_id: int
    expires_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConflictResolvedByUserEvent(DomainEvent):
    """
    Evento disparado quando um conflito é resolvido pela escolha do usuário.

    Attributes:
        aggregate_id: ID do conflito
        conflict_id: ID do conflito
        cpf_hash: Hash do CPF
        chosen_user_id: ID do usuário escolhido para manter
        removed_user_ids: IDs dos usuários que serão removidos
        resolved_by: ID do usuário que resolveu
        resolved_at: Data da resolução
        occurred_at: Timestamp do evento
    """
    conflict_id: str
    cpf_hash: str
    chosen_user_id: int
    removed_user_ids: List[int]
    resolved_by: int
    resolved_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConflictExpiredEvent(DomainEvent):
    """
    Evento disparado quando um conflito expira sem resolução.

    Attributes:
        aggregate_id: ID do conflito
        conflict_id: ID do conflito
        cpf_hash: Hash do CPF
        user_ids: IDs de todos os usuários que serão removidos
        notified_user_id: ID do usuário que foi notificado
        expired_at: Data da expiração
        expires_at: Data limite que foi ultrapassada
        occurred_at: Timestamp do evento
    """
    conflict_id: str
    cpf_hash: str
    user_ids: List[int]
    notified_user_id: int
    expired_at: datetime
    expires_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class ConflictResolvedByAdminEvent(DomainEvent):
    """
    Evento disparado quando um conflito é resolvido por um administrador.

    Attributes:
        aggregate_id: ID do conflito
        conflict_id: ID do conflito
        cpf_hash: Hash do CPF
        admin_user_id: ID do administrador
        chosen_user_id: ID do usuário escolhido (None = remove todos)
        removed_user_ids: IDs dos usuários removidos
        notes: Notas do administrador
        resolved_at: Data da resolução
        occurred_at: Timestamp do evento
    """
    conflict_id: str
    cpf_hash: str
    admin_user_id: int
    chosen_user_id: Optional[int]
    removed_user_ids: List[int]
    notes: Optional[str]
    resolved_at: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()
