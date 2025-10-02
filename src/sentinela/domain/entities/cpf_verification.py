"""
CPF Verification Entity.

Representa o processo de verificação de CPF de um usuário,
incluindo todo o ciclo de vida da verificação.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any

from .base import AggregateRoot
from ..value_objects.identifiers import UserId
from ..value_objects.cpf import CPF


class VerificationType(Enum):
    """Tipos de verificação de CPF."""
    AUTO_CHECKUP = "auto_checkup"
    SUPPORT_REQUEST = "support_request"
    MANUAL_REVIEW = "manual_review"
    SECURITY_CHECK = "security_check"


class VerificationStatus(Enum):
    """Status da verificação."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VerificationAttempt:
    """
    Representa uma tentativa de verificação.

    Attributes:
        attempted_at: Timestamp da tentativa
        cpf_provided: CPF fornecido na tentativa
        success: Se a tentativa foi bem-sucedida
        failure_reason: Motivo da falha (se aplicável)
    """

    def __init__(self, cpf_provided: str, success: bool = False, failure_reason: Optional[str] = None):
        self.attempted_at = datetime.now()
        self.cpf_provided = cpf_provided
        self.success = success
        self.failure_reason = failure_reason


@dataclass(frozen=True)
class VerificationId:
    """ID único de verificação."""
    value: str

    @classmethod
    def generate(cls) -> 'VerificationId':
        """Gera um novo ID de verificação."""
        import uuid
        return cls(str(uuid.uuid4()))


class CPFVerificationRequest(AggregateRoot[VerificationId]):
    """
    Aggregate root para solicitações de verificação de CPF.

    Gerencia todo o ciclo de vida de uma verificação,
    desde a criação até a conclusão ou expiração.
    """

    def __init__(
        self,
        verification_id: VerificationId,
        user_id: UserId,
        username: str,
        user_mention: str,
        verification_type: VerificationType,
        source_action: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        super().__init__(verification_id)
        self._user_id = user_id
        self._username = username
        self._user_mention = user_mention
        self._verification_type = verification_type
        self._source_action = source_action
        self._status = VerificationStatus.PENDING
        self._created_at = datetime.now()
        self._expires_at = expires_at or (datetime.now() + timedelta(hours=24))
        self._attempts: list[VerificationAttempt] = []
        self._completed_at: Optional[datetime] = None
        self._cpf_verified: Optional[CPF] = None
        self._client_data: Optional[Dict[str, Any]] = None

    # Properties
    @property
    def user_id(self) -> UserId:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def user_mention(self) -> str:
        return self._user_mention

    @property
    def verification_type(self) -> VerificationType:
        return self._verification_type

    @property
    def source_action(self) -> Optional[str]:
        return self._source_action

    @property
    def status(self) -> VerificationStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def attempts(self) -> list[VerificationAttempt]:
        return self._attempts.copy()

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def cpf_verified(self) -> Optional[CPF]:
        return self._cpf_verified

    @property
    def client_data(self) -> Optional[Dict[str, Any]]:
        return self._client_data

    @property
    def cpf_hash(self) -> str:
        """Retorna hash do CPF para armazenamento e busca."""
        if self._cpf_verified:
            # Usa hash do CPF verificado
            from ..services.cpf_validation_service import CPFValidationService
            return CPFValidationService.hash_cpf(str(self._cpf_verified))
        else:
            # Antes da verificação, usa hash do user_id como placeholder
            import hashlib
            return hashlib.sha256(f"pending_{self._user_id.value}".encode()).hexdigest()

    # Business rules
    def is_expired(self) -> bool:
        """Verifica se a verificação expirou."""
        return datetime.now() > self._expires_at

    def can_attempt(self) -> bool:
        """Verifica se ainda é possível fazer tentativas."""
        max_attempts = 3
        return (
            self._status in (VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS) and
            self.attempt_count < max_attempts and
            not self.is_expired()
        )

    def has_attempts_left(self) -> int:
        """Retorna quantas tentativas ainda restam."""
        max_attempts = 3
        return max(0, max_attempts - self.attempt_count)

    def start_verification(self) -> None:
        """Inicia o processo de verificação."""
        if self._status != VerificationStatus.PENDING:
            raise VerificationBusinessRuleError(
                f"Não é possível iniciar verificação com status {self._status.value}"
            )

        if self.is_expired():
            self._expire_verification()
            raise VerificationBusinessRuleError("Verificação expirada")

        self._status = VerificationStatus.IN_PROGRESS

        # Emite evento
        from ..events.verification_events import VerificationStarted
        self.add_domain_event(VerificationStarted(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            verification_type=self._verification_type.value
        ))

    def add_attempt(self, cpf_provided: str, success: bool = False, failure_reason: Optional[str] = None) -> None:
        """
        Adiciona uma tentativa de verificação.

        Args:
            cpf_provided: CPF fornecido pelo usuário
            success: Se a tentativa foi bem-sucedida
            failure_reason: Motivo da falha (se aplicável)

        Raises:
            VerificationBusinessRuleError: Se não é possível adicionar tentativa
        """
        if not self.can_attempt():
            raise VerificationBusinessRuleError("Não é possível adicionar mais tentativas")

        attempt = VerificationAttempt(cpf_provided, success, failure_reason)
        self._attempts.append(attempt)

        # Emite evento de tentativa
        from ..events.verification_events import VerificationAttemptMade
        self.add_domain_event(VerificationAttemptMade(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            attempt_number=len(self._attempts),
            success=success,
            cpf_provided=cpf_provided[:3] + "***" + cpf_provided[-2:] if cpf_provided else None  # Mascarado
        ))

        # Se foi bem-sucedida, completa a verificação
        if success:
            self._complete_verification_success(cpf_provided)

        # Se esgotou tentativas, falha a verificação
        elif not self.has_attempts_left():
            self._fail_verification("Muitas tentativas falhas")

    def complete_with_success(self, cpf: CPF, client_data: Dict[str, Any]) -> None:
        """
        Completa verificação com sucesso.

        Args:
            cpf: CPF verificado
            client_data: Dados do cliente do HubSoft

        Raises:
            VerificationBusinessRuleError: Se verificação não pode ser completada
        """
        if self._status not in (VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS):
            raise VerificationBusinessRuleError(
                f"Não é possível completar verificação com status {self._status.value}"
            )

        self._status = VerificationStatus.COMPLETED
        self._completed_at = datetime.now()
        self._cpf_verified = cpf
        self._client_data = client_data

        # Emite evento de sucesso
        from ..events.verification_events import VerificationCompleted
        self.add_domain_event(VerificationCompleted(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            verification_type=self._verification_type.value,
            cpf_number=str(cpf),
            success=True
        ))

    def fail_verification(self, reason: str) -> None:
        """
        Falha a verificação.

        Args:
            reason: Motivo da falha
        """
        if self._status in (VerificationStatus.COMPLETED, VerificationStatus.FAILED):
            return  # Já finalizada

        self._status = VerificationStatus.FAILED
        self._completed_at = datetime.now()

        # Emite evento de falha
        from ..events.verification_events import VerificationFailed
        self.add_domain_event(VerificationFailed(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            verification_type=self._verification_type.value,
            reason=reason,
            attempt_count=self.attempt_count
        ))

    def cancel_verification(self, reason: str = "Cancelado pelo usuário") -> None:
        """
        Cancela a verificação.

        Args:
            reason: Motivo do cancelamento
        """
        if self._status in (VerificationStatus.COMPLETED, VerificationStatus.FAILED, VerificationStatus.EXPIRED):
            raise VerificationBusinessRuleError("Não é possível cancelar verificação finalizada")

        self._status = VerificationStatus.CANCELLED
        self._completed_at = datetime.now()

        # Emite evento de cancelamento
        from ..events.verification_events import VerificationCancelled
        self.add_domain_event(VerificationCancelled(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            reason=reason
        ))

    def expire_verification(self) -> None:
        """Expira a verificação por timeout."""
        if self._status in (VerificationStatus.COMPLETED, VerificationStatus.FAILED):
            return  # Já finalizada

        self._status = VerificationStatus.EXPIRED
        self._completed_at = datetime.now()

        # Emite evento de expiração
        from ..events.verification_events import VerificationExpired
        self.add_domain_event(VerificationExpired(
            verification_id=self.id,
            user_id=self._user_id.value,
            username=self._username,
            verification_type=self._verification_type.value,
            expires_at=self._expires_at
        ))

    def _complete_verification_success(self, cpf_provided: str) -> None:
        """Lógica interna para completar verificação com sucesso."""
        # Será chamado pelo use case após validações externas
        pass

    def _fail_verification(self, reason: str) -> None:
        """Lógica interna para falhar verificação."""
        self.fail_verification(reason)

    def _expire_verification(self) -> None:
        """Lógica interna para expirar verificação."""
        self.expire_verification()

    def get_time_remaining(self) -> timedelta:
        """Retorna tempo restante até expiração."""
        if self.is_expired():
            return timedelta(0)
        return self._expires_at - datetime.now()

    def get_attempts_summary(self) -> Dict[str, Any]:
        """Retorna resumo das tentativas."""
        successful_attempts = [a for a in self._attempts if a.success]
        failed_attempts = [a for a in self._attempts if not a.success]

        return {
            "total": len(self._attempts),
            "successful": len(successful_attempts),
            "failed": len(failed_attempts),
            "remaining": self.has_attempts_left(),
            "last_attempt": self._attempts[-1].attempted_at if self._attempts else None
        }


class VerificationBusinessRuleError(Exception):
    """Erro de regra de negócio para verificações."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}