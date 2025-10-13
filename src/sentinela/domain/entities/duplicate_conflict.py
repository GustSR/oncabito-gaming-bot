"""
Duplicate Conflict Entity.

Representa um conflito de CPF duplicado detectado pelo sistema,
gerenciando todo o processo de resolução até conclusão ou timeout.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List

from .base import AggregateRoot


class ConflictStatus(Enum):
    """Status do conflito de duplicata."""
    PENDING = "PENDING"  # Aguardando resposta do usuário
    RESOLVED = "RESOLVED"  # Resolvido pela escolha do usuário
    EXPIRED_REMOVED = "EXPIRED_REMOVED"  # Expirado, todas as contas removidas
    ADMIN_RESOLVED = "ADMIN_RESOLVED"  # Resolvido por intervenção de admin


class ResolutionAction(Enum):
    """Ação tomada para resolver o conflito."""
    USER_CHOICE = "USER_CHOICE"  # Usuário escolheu qual conta manter
    TIMEOUT_REMOVAL = "TIMEOUT_REMOVAL"  # Timeout, todas as contas removidas
    ADMIN_INTERVENTION = "ADMIN_INTERVENTION"  # Admin resolveu manualmente


@dataclass(frozen=True)
class ConflictId:
    """ID único de conflito."""
    value: str

    @classmethod
    def generate(cls) -> 'ConflictId':
        """Gera um novo ID de conflito."""
        import uuid
        return cls(str(uuid.uuid4()))


class DuplicateConflict(AggregateRoot[ConflictId]):
    """
    Aggregate root para conflitos de CPF duplicado.

    Gerencia todo o ciclo de vida de um conflito de duplicata,
    desde a detecção até a resolução ou remoção por timeout.
    """

    def __init__(
        self,
        conflict_id: ConflictId,
        cpf_hash: str,
        user_ids: List[int],
        notified_user_id: int,
        conflict_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        resolution_timeout_hours: int = 24
    ):
        """
        Cria um novo conflito de duplicata.

        Args:
            conflict_id: ID único do conflito
            cpf_hash: Hash do CPF duplicado
            user_ids: Lista de IDs dos usuários envolvidos
            notified_user_id: ID do usuário que será notificado (mais recente)
            conflict_data: Dados adicionais do conflito (usernames, etc)
            expires_at: Data de expiração (opcional, padrão 24h)
            resolution_timeout_hours: Horas até timeout (padrão 24h)
        """
        super().__init__(conflict_id)
        self._cpf_hash = cpf_hash
        self._user_ids = user_ids
        self._notified_user_id = notified_user_id
        self._conflict_data = conflict_data or {}
        self._status = ConflictStatus.PENDING
        self._created_at = datetime.now()
        self._expires_at = expires_at or (datetime.now() + timedelta(hours=resolution_timeout_hours))
        self._resolved_at: Optional[datetime] = None
        self._resolved_by: Optional[int] = None
        self._resolution_choice: Optional[int] = None
        self._resolution_action: Optional[ResolutionAction] = None

    # Properties
    @property
    def cpf_hash(self) -> str:
        """Hash do CPF em conflito."""
        return self._cpf_hash

    @property
    def user_ids(self) -> List[int]:
        """IDs dos usuários envolvidos no conflito."""
        return self._user_ids.copy()

    @property
    def notified_user_id(self) -> int:
        """ID do usuário que foi notificado."""
        return self._notified_user_id

    @property
    def conflict_data(self) -> Dict[str, Any]:
        """Dados adicionais do conflito."""
        return self._conflict_data.copy()

    @property
    def status(self) -> ConflictStatus:
        """Status atual do conflito."""
        return self._status

    @property
    def created_at(self) -> datetime:
        """Data de criação do conflito."""
        return self._created_at

    @property
    def expires_at(self) -> datetime:
        """Data de expiração do conflito."""
        return self._expires_at

    @property
    def resolved_at(self) -> Optional[datetime]:
        """Data de resolução do conflito."""
        return self._resolved_at

    @property
    def resolved_by(self) -> Optional[int]:
        """ID do usuário que resolveu o conflito."""
        return self._resolved_by

    @property
    def resolution_choice(self) -> Optional[int]:
        """ID do usuário escolhido para manter o CPF."""
        return self._resolution_choice

    @property
    def resolution_action(self) -> Optional[ResolutionAction]:
        """Ação tomada para resolver o conflito."""
        return self._resolution_action

    # Business rules
    def is_expired(self) -> bool:
        """Verifica se o conflito expirou."""
        return datetime.now() > self._expires_at

    def is_pending(self) -> bool:
        """Verifica se o conflito está pendente."""
        return self._status == ConflictStatus.PENDING

    def can_be_resolved(self) -> bool:
        """Verifica se o conflito pode ser resolvido."""
        return self._status == ConflictStatus.PENDING and not self.is_expired()

    def get_time_remaining(self) -> timedelta:
        """Retorna tempo restante até expiração."""
        if self.is_expired():
            return timedelta(0)
        return self._expires_at - datetime.now()

    def resolve_by_user_choice(
        self,
        chosen_user_id: int,
        resolved_by: int
    ) -> None:
        """
        Resolve o conflito pela escolha do usuário.

        Args:
            chosen_user_id: ID do usuário escolhido para manter
            resolved_by: ID do usuário que fez a escolha

        Raises:
            ConflictBusinessRuleError: Se o conflito não pode ser resolvido
        """
        if not self.can_be_resolved():
            raise ConflictBusinessRuleError(
                f"Conflito não pode ser resolvido. Status: {self._status.value}, "
                f"Expirado: {self.is_expired()}"
            )

        if chosen_user_id not in self._user_ids:
            raise ConflictBusinessRuleError(
                f"Usuário escolhido {chosen_user_id} não está na lista de conflitos"
            )

        self._status = ConflictStatus.RESOLVED
        self._resolved_at = datetime.now()
        self._resolved_by = resolved_by
        self._resolution_choice = chosen_user_id
        self._resolution_action = ResolutionAction.USER_CHOICE

        # Emite evento de resolução
        from ..events.conflict_events import ConflictResolvedByUserEvent
        self.add_domain_event(ConflictResolvedByUserEvent(
            aggregate_id=str(self.id.value),
            conflict_id=str(self.id.value),
            cpf_hash=self._cpf_hash,
            chosen_user_id=chosen_user_id,
            removed_user_ids=[uid for uid in self._user_ids if uid != chosen_user_id],
            resolved_by=resolved_by,
            resolved_at=self._resolved_at
        ))

    def expire_and_remove_all(self) -> None:
        """
        Expira o conflito e marca para remoção de todas as contas.

        Raises:
            ConflictBusinessRuleError: Se o conflito não está pendente
        """
        if not self.is_pending():
            raise ConflictBusinessRuleError(
                f"Conflito não pode ser expirado. Status atual: {self._status.value}"
            )

        self._status = ConflictStatus.EXPIRED_REMOVED
        self._resolved_at = datetime.now()
        self._resolution_action = ResolutionAction.TIMEOUT_REMOVAL

        # Emite evento de expiração
        from ..events.conflict_events import ConflictExpiredEvent
        self.add_domain_event(ConflictExpiredEvent(
            aggregate_id=str(self.id.value),
            conflict_id=str(self.id.value),
            cpf_hash=self._cpf_hash,
            user_ids=self._user_ids,
            notified_user_id=self._notified_user_id,
            expired_at=self._resolved_at,
            expires_at=self._expires_at
        ))

    def resolve_by_admin(
        self,
        admin_user_id: int,
        chosen_user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Resolve o conflito por intervenção de admin.

        Args:
            admin_user_id: ID do administrador
            chosen_user_id: ID do usuário escolhido (opcional, None remove todos)
            notes: Notas sobre a resolução

        Raises:
            ConflictBusinessRuleError: Se o conflito não está pendente
        """
        if not self.is_pending():
            raise ConflictBusinessRuleError(
                f"Conflito não pode ser resolvido por admin. Status: {self._status.value}"
            )

        if chosen_user_id and chosen_user_id not in self._user_ids:
            raise ConflictBusinessRuleError(
                f"Usuário escolhido {chosen_user_id} não está na lista de conflitos"
            )

        self._status = ConflictStatus.ADMIN_RESOLVED
        self._resolved_at = datetime.now()
        self._resolved_by = admin_user_id
        self._resolution_choice = chosen_user_id
        self._resolution_action = ResolutionAction.ADMIN_INTERVENTION

        if notes:
            self._conflict_data['admin_notes'] = notes
            self._conflict_data['admin_resolved_at'] = self._resolved_at.isoformat()

        # Emite evento de resolução por admin
        from ..events.conflict_events import ConflictResolvedByAdminEvent
        self.add_domain_event(ConflictResolvedByAdminEvent(
            aggregate_id=str(self.id.value),
            conflict_id=str(self.id.value),
            cpf_hash=self._cpf_hash,
            admin_user_id=admin_user_id,
            chosen_user_id=chosen_user_id,
            removed_user_ids=[uid for uid in self._user_ids if uid != chosen_user_id] if chosen_user_id else self._user_ids,
            notes=notes,
            resolved_at=self._resolved_at
        ))

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo do conflito."""
        return {
            "conflict_id": str(self.id.value),
            "cpf_hash": self._cpf_hash,
            "user_count": len(self._user_ids),
            "user_ids": self._user_ids,
            "notified_user_id": self._notified_user_id,
            "status": self._status.value,
            "created_at": self._created_at.isoformat(),
            "expires_at": self._expires_at.isoformat(),
            "time_remaining": str(self.get_time_remaining()),
            "is_expired": self.is_expired(),
            "resolved_at": self._resolved_at.isoformat() if self._resolved_at else None,
            "resolved_by": self._resolved_by,
            "resolution_choice": self._resolution_choice,
            "resolution_action": self._resolution_action.value if self._resolution_action else None
        }


class ConflictBusinessRuleError(Exception):
    """Erro de regra de negócio para conflitos."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}
