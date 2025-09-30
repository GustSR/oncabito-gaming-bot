"""
Group Member Entity.

Representa um membro do grupo OnCabo Gaming no Telegram.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from .base import Entity
from ..value_objects.identifiers import UserId


class MemberStatus(Enum):
    """Status do membro no grupo."""

    CREATOR = "creator"          # Criador do grupo
    ADMINISTRATOR = "administrator"  # Administrador
    MEMBER = "member"            # Membro ativo
    RESTRICTED = "restricted"    # Membro restrito
    LEFT = "left"               # Saiu do grupo
    KICKED = "kicked"           # Foi removido


class MemberRole(Enum):
    """Papel/função do membro."""

    OWNER = "owner"              # Dono
    ADMIN = "admin"              # Admin
    MODERATOR = "moderator"      # Moderador
    GAMER_VERIFIED = "gamer_verified"  # Gamer verificado
    GAMER = "gamer"              # Gamer normal
    NEW_MEMBER = "new_member"    # Novo membro
    GUEST = "guest"              # Convidado


@dataclass
class GroupMember(Entity):
    """
    Representa um membro do grupo.

    Attributes:
        user_id: ID do usuário (identidade única)
        telegram_id: ID no Telegram
        username: Nome de usuário no Telegram
        first_name: Primeiro nome
        last_name: Sobrenome (opcional)
        status: Status atual no grupo
        role: Papel/função no grupo
        joined_at: Data de entrada no grupo
        left_at: Data de saída (se aplicável)
        is_verified: Se está verificado via CPF
        is_active_contract: Se tem contrato ativo
        last_activity: Última atividade registrada
        message_count: Contador de mensagens
        warnings_count: Número de advertências
        kick_reason: Motivo da remoção (se aplicável)
    """

    user_id: UserId
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str] = None
    status: MemberStatus = MemberStatus.MEMBER
    role: MemberRole = MemberRole.NEW_MEMBER
    joined_at: datetime = field(default_factory=datetime.now)
    left_at: Optional[datetime] = None
    is_verified: bool = False
    is_active_contract: bool = True
    last_activity: Optional[datetime] = None
    message_count: int = 0
    warnings_count: int = 0
    kick_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_active_member(self) -> bool:
        """Verifica se é membro ativo do grupo."""
        active_statuses = [
            MemberStatus.CREATOR,
            MemberStatus.ADMINISTRATOR,
            MemberStatus.MEMBER,
            MemberStatus.RESTRICTED
        ]
        return self.status in active_statuses

    def is_admin_or_higher(self) -> bool:
        """Verifica se é administrador ou superior."""
        return self.status in [MemberStatus.CREATOR, MemberStatus.ADMINISTRATOR]

    def can_be_removed(self) -> bool:
        """Verifica se pode ser removido do grupo."""
        # Criador e administradores não podem ser removidos automaticamente
        if self.status in [MemberStatus.CREATOR, MemberStatus.ADMINISTRATOR]:
            return False

        # Membros já removidos não precisam ser removidos novamente
        if self.status in [MemberStatus.LEFT, MemberStatus.KICKED]:
            return False

        return True

    def mark_as_left(self) -> None:
        """Marca membro como tendo saído do grupo."""
        self.status = MemberStatus.LEFT
        self.left_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_as_kicked(self, reason: str) -> None:
        """
        Marca membro como removido do grupo.

        Args:
            reason: Motivo da remoção
        """
        self.status = MemberStatus.KICKED
        self.left_at = datetime.now()
        self.kick_reason = reason
        self.updated_at = datetime.now()

    def promote_to_verified_gamer(self) -> None:
        """Promove para gamer verificado."""
        if self.role in [MemberRole.NEW_MEMBER, MemberRole.GUEST, MemberRole.GAMER]:
            self.role = MemberRole.GAMER_VERIFIED
            self.is_verified = True
            self.updated_at = datetime.now()

    def add_warning(self) -> int:
        """
        Adiciona uma advertência ao membro.

        Returns:
            int: Número total de advertências
        """
        self.warnings_count += 1
        self.updated_at = datetime.now()
        return self.warnings_count

    def update_last_activity(self) -> None:
        """Atualiza timestamp da última atividade."""
        self.last_activity = datetime.now()
        self.updated_at = datetime.now()

    def increment_message_count(self) -> int:
        """
        Incrementa contador de mensagens.

        Returns:
            int: Número total de mensagens
        """
        self.message_count += 1
        self.update_last_activity()
        return self.message_count

    def should_be_removed_for_inactivity(self, days_threshold: int = 30) -> bool:
        """
        Verifica se deve ser removido por inatividade.

        Args:
            days_threshold: Dias de inatividade permitidos

        Returns:
            bool: True se deve ser removido
        """
        if not self.can_be_removed():
            return False

        if not self.last_activity:
            # Se nunca teve atividade, verifica baseado na data de entrada
            days_since_join = (datetime.now() - self.joined_at).days
            return days_since_join > days_threshold

        days_inactive = (datetime.now() - self.last_activity).days
        return days_inactive > days_threshold

    def get_member_display_name(self) -> str:
        """Retorna nome formatado para exibição."""
        if self.username:
            return f"@{self.username}"
        elif self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.first_name

    def to_dict(self) -> dict:
        """Converte entidade para dicionário."""
        return {
            'id': self.id.value,
            'user_id': self.user_id.value,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'status': self.status.value,
            'role': self.role.value,
            'joined_at': self.joined_at.isoformat(),
            'left_at': self.left_at.isoformat() if self.left_at else None,
            'is_verified': self.is_verified,
            'is_active_contract': self.is_active_contract,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'message_count': self.message_count,
            'warnings_count': self.warnings_count,
            'kick_reason': self.kick_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }