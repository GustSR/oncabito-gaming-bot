"""
Permission Level Value Object.

Define os níveis de permissão para usuários no sistema.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Set


class PermissionLevel(Enum):
    """Níveis de permissão no sistema."""

    RESTRICTED = "restricted"  # Usuário restrito (novo membro)
    VERIFIED = "verified"      # Usuário verificado (acesso básico)
    GAMER = "gamer"           # Gamer verificado (acesso a tópicos gaming)
    MODERATOR = "moderator"   # Moderador
    ADMIN = "admin"           # Administrador
    OWNER = "owner"           # Proprietário


@dataclass(frozen=True)
class TopicAccess:
    """Representa acesso a um tópico específico."""

    topic_id: int
    topic_name: str
    can_read: bool = True
    can_write: bool = True
    can_send_media: bool = True
    can_send_polls: bool = False


@dataclass(frozen=True)
class UserPermissions:
    """
    Representa as permissões completas de um usuário.

    Value Object que encapsula todas as permissões e capacidades
    de um usuário no sistema.
    """

    level: PermissionLevel
    can_send_messages: bool
    can_send_media: bool
    can_send_polls: bool
    can_send_other_messages: bool
    topic_access: Set[int]  # IDs dos tópicos que o usuário pode acessar
    is_promoted: bool = False
    is_banned: bool = False

    def has_topic_access(self, topic_id: int) -> bool:
        """Verifica se usuário tem acesso a um tópico específico."""
        return topic_id in self.topic_access

    def has_gaming_access(self) -> bool:
        """Verifica se usuário tem acesso aos tópicos de gaming."""
        return self.level in [
            PermissionLevel.GAMER,
            PermissionLevel.MODERATOR,
            PermissionLevel.ADMIN,
            PermissionLevel.OWNER
        ]

    def can_moderate(self) -> bool:
        """Verifica se usuário pode moderar."""
        return self.level in [
            PermissionLevel.MODERATOR,
            PermissionLevel.ADMIN,
            PermissionLevel.OWNER
        ]

    def can_administrate(self) -> bool:
        """Verifica se usuário pode administrar."""
        return self.level in [
            PermissionLevel.ADMIN,
            PermissionLevel.OWNER
        ]

    @classmethod
    def create_restricted(cls) -> 'UserPermissions':
        """Cria permissões para usuário restrito (novo membro)."""
        return cls(
            level=PermissionLevel.RESTRICTED,
            can_send_messages=False,
            can_send_media=False,
            can_send_polls=False,
            can_send_other_messages=False,
            topic_access=set(),
            is_promoted=False,
            is_banned=False
        )

    @classmethod
    def create_verified(cls, topic_access: Set[int] = None) -> 'UserPermissions':
        """Cria permissões para usuário verificado."""
        return cls(
            level=PermissionLevel.VERIFIED,
            can_send_messages=True,
            can_send_media=True,
            can_send_polls=False,
            can_send_other_messages=True,
            topic_access=topic_access or set(),
            is_promoted=False,
            is_banned=False
        )

    @classmethod
    def create_gamer(cls, topic_access: Set[int]) -> 'UserPermissions':
        """Cria permissões para gamer verificado com acesso a tópicos."""
        return cls(
            level=PermissionLevel.GAMER,
            can_send_messages=True,
            can_send_media=True,
            can_send_polls=True,
            can_send_other_messages=True,
            topic_access=topic_access,
            is_promoted=True,
            is_banned=False
        )

    @classmethod
    def create_moderator(cls, topic_access: Set[int]) -> 'UserPermissions':
        """Cria permissões para moderador."""
        return cls(
            level=PermissionLevel.MODERATOR,
            can_send_messages=True,
            can_send_media=True,
            can_send_polls=True,
            can_send_other_messages=True,
            topic_access=topic_access,
            is_promoted=True,
            is_banned=False
        )

    def grant_gaming_access(self, gaming_topics: Set[int]) -> 'UserPermissions':
        """Concede acesso aos tópicos de gaming."""
        if self.level == PermissionLevel.RESTRICTED or self.level == PermissionLevel.VERIFIED:
            # Promove para Gamer
            return UserPermissions.create_gamer(
                topic_access=self.topic_access.union(gaming_topics)
            )
        return self

    def revoke_access(self) -> 'UserPermissions':
        """Revoga todo acesso (bane o usuário)."""
        return UserPermissions(
            level=self.level,
            can_send_messages=False,
            can_send_media=False,
            can_send_polls=False,
            can_send_other_messages=False,
            topic_access=set(),
            is_promoted=False,
            is_banned=True
        )