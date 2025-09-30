"""
Invite Link Entity.

Representa um link de convite para o grupo.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from .base import Entity
from ..value_objects.identifiers import UserId


class InviteLinkStatus(Enum):
    """Status do link de convite."""

    ACTIVE = "active"        # Ativo e válido
    USED = "used"           # Usado (limite atingido)
    EXPIRED = "expired"     # Expirado por tempo
    REVOKED = "revoked"     # Revogado manualmente


@dataclass
class InviteLink(Entity):
    """
    Representa um link de convite do Telegram.

    Attributes:
        created_for_user: Usuário para quem foi criado
        created_by: Quem criou o link
        invite_url: URL do link de convite
        name: Nome descritivo do link
        expire_date: Data de expiração
        member_limit: Limite de membros que podem usar
        creates_join_request: Se cria solicitação de entrada
        status: Status atual do link
        used_count: Quantas vezes foi usado
        used_by: IDs dos usuários que usaram
        revoked_at: Data de revogação (se aplicável)
        revoked_reason: Motivo da revogação
    """

    created_for_user: UserId
    created_by: UserId
    invite_url: str
    name: str
    expire_date: datetime
    member_limit: int = 1
    creates_join_request: bool = False
    status: InviteLinkStatus = InviteLinkStatus.ACTIVE
    used_count: int = 0
    used_by: list = field(default_factory=list)
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_valid(self) -> bool:
        """
        Verifica se o link ainda é válido.

        Returns:
            bool: True se válido
        """
        # Verifica status
        if self.status != InviteLinkStatus.ACTIVE:
            return False

        # Verifica expiração
        if datetime.now() > self.expire_date:
            self.mark_as_expired()
            return False

        # Verifica limite de uso
        if self.used_count >= self.member_limit:
            self.mark_as_used()
            return False

        return True

    def can_be_used_by(self, user_id: UserId) -> bool:
        """
        Verifica se pode ser usado por um usuário específico.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se pode ser usado
        """
        if not self.is_valid():
            return False

        # Se o link foi criado para um usuário específico
        if self.created_for_user != user_id:
            return False

        # Se o usuário já usou
        if user_id.value in self.used_by:
            return False

        return True

    def mark_as_used(self, user_id: Optional[UserId] = None) -> None:
        """
        Marca link como usado.

        Args:
            user_id: ID do usuário que usou (opcional)
        """
        self.used_count += 1

        if user_id and user_id.value not in self.used_by:
            self.used_by.append(user_id.value)

        if self.used_count >= self.member_limit:
            self.status = InviteLinkStatus.USED

        self.updated_at = datetime.now()

    def mark_as_expired(self) -> None:
        """Marca link como expirado."""
        self.status = InviteLinkStatus.EXPIRED
        self.updated_at = datetime.now()

    def revoke(self, reason: str = "Manual revocation") -> None:
        """
        Revoga o link.

        Args:
            reason: Motivo da revogação
        """
        self.status = InviteLinkStatus.REVOKED
        self.revoked_at = datetime.now()
        self.revoked_reason = reason
        self.updated_at = datetime.now()

    def get_time_until_expiry(self) -> timedelta:
        """
        Calcula tempo até expiração.

        Returns:
            timedelta: Tempo restante
        """
        return self.expire_date - datetime.now()

    def is_expired(self) -> bool:
        """Verifica se está expirado."""
        return datetime.now() > self.expire_date

    def get_remaining_uses(self) -> int:
        """
        Retorna número de usos restantes.

        Returns:
            int: Usos restantes
        """
        return max(0, self.member_limit - self.used_count)

    def to_dict(self) -> dict:
        """Converte entidade para dicionário."""
        return {
            'id': self.id.value,
            'created_for_user': self.created_for_user.value,
            'created_by': self.created_by.value,
            'invite_url': self.invite_url,
            'name': self.name,
            'expire_date': self.expire_date.isoformat(),
            'member_limit': self.member_limit,
            'creates_join_request': self.creates_join_request,
            'status': self.status.value,
            'used_count': self.used_count,
            'used_by': self.used_by,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'revoked_reason': self.revoked_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }