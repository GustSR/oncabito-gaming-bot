"""
HubSoft Integration Entity.

Representa operações de integração com o sistema HubSoft,
incluindo sincronização de tickets, usuários e dados de clientes.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json

from .base import AggregateRoot
from ..value_objects.identifiers import TicketId, UserId, HubSoftId


class IntegrationType(Enum):
    """Tipos de integração com HubSoft."""
    TICKET_SYNC = "ticket_sync"
    USER_VERIFICATION = "user_verification"
    CLIENT_DATA_FETCH = "client_data_fetch"
    STATUS_UPDATE = "status_update"
    BULK_SYNC = "bulk_sync"


class IntegrationStatus(Enum):
    """Status da operação de integração."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"


class IntegrationPriority(Enum):
    """Prioridade da integração."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class IntegrationId:
    """ID único de integração."""
    value: str

    @classmethod
    def generate(cls) -> 'IntegrationId':
        """Gera um novo ID de integração."""
        import uuid
        return cls(str(uuid.uuid4()))


@dataclass
class IntegrationAttempt:
    """
    Representa uma tentativa de integração.

    Attributes:
        attempted_at: Timestamp da tentativa
        success: Se a tentativa foi bem-sucedida
        error_message: Mensagem de erro (se aplicável)
        response_data: Dados de resposta do HubSoft
        duration_ms: Duração da tentativa em milissegundos
    """
    attempted_at: datetime
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None


class HubSoftIntegrationRequest(AggregateRoot[IntegrationId]):
    """
    Aggregate root para solicitações de integração com HubSoft.

    Gerencia todo o ciclo de vida de uma integração,
    incluindo tentativas, retry logic e tratamento de erros.
    """

    def __init__(
        self,
        integration_id: IntegrationId,
        integration_type: IntegrationType,
        priority: IntegrationPriority = IntegrationPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout_seconds: int = 30
    ):
        super().__init__(integration_id)
        self._integration_type = integration_type
        self._priority = priority
        self._status = IntegrationStatus.PENDING
        self._payload = payload or {}
        self._metadata = metadata or {}
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._attempts: List[IntegrationAttempt] = []
        self._scheduled_at: Optional[datetime] = None
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._hubsoft_response: Optional[Dict[str, Any]] = None
        self._error_details: Optional[Dict[str, Any]] = None

    # Properties
    @property
    def integration_type(self) -> IntegrationType:
        return self._integration_type

    @property
    def priority(self) -> IntegrationPriority:
        return self._priority

    @property
    def status(self) -> IntegrationStatus:
        return self._status

    @property
    def payload(self) -> Dict[str, Any]:
        return self._payload.copy()

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata.copy()

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def attempts(self) -> List[IntegrationAttempt]:
        return self._attempts.copy()

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def scheduled_at(self) -> Optional[datetime]:
        return self._scheduled_at

    @property
    def started_at(self) -> Optional[datetime]:
        return self._started_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def hubsoft_response(self) -> Optional[Dict[str, Any]]:
        return self._hubsoft_response.copy() if self._hubsoft_response else None

    @property
    def error_details(self) -> Optional[Dict[str, Any]]:
        return self._error_details.copy() if self._error_details else None

    # Business rules
    def can_retry(self) -> bool:
        """Verifica se ainda é possível fazer retry."""
        return (
            self._status in (IntegrationStatus.FAILED, IntegrationStatus.RETRY_SCHEDULED) and
            self.attempt_count < self._max_retries
        )

    def should_retry(self, error_type: str) -> bool:
        """Verifica se erro específico deve ser retentado."""
        retryable_errors = {
            "timeout", "connection_error", "rate_limit",
            "server_error", "temporary_unavailable"
        }
        return error_type in retryable_errors and self.can_retry()

    def get_retry_delay(self) -> int:
        """Calcula delay para próximo retry (backoff exponencial)."""
        base_delay = 60  # 1 minuto
        return min(base_delay * (2 ** self.attempt_count), 3600)  # Máx 1 hora

    def is_high_priority(self) -> bool:
        """Verifica se é alta prioridade."""
        return self._priority in (IntegrationPriority.HIGH, IntegrationPriority.URGENT)

    def schedule_integration(self, scheduled_at: Optional[datetime] = None) -> None:
        """
        Agenda a integração para execução.

        Args:
            scheduled_at: Quando executar (None = imediato)
        """
        if self._status != IntegrationStatus.PENDING:
            raise IntegrationBusinessRuleError(
                f"Não é possível agendar integração com status {self._status.value}"
            )

        self._scheduled_at = scheduled_at or datetime.now()

        # Emite evento
        from ..events.hubsoft_events import IntegrationScheduled
        self.add_domain_event(IntegrationScheduled(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            priority=self._priority.value,
            scheduled_at=self._scheduled_at
        ))

    def start_integration(self) -> None:
        """Inicia a execução da integração."""
        if self._status not in (IntegrationStatus.PENDING, IntegrationStatus.RETRY_SCHEDULED):
            raise IntegrationBusinessRuleError(
                f"Não é possível iniciar integração com status {self._status.value}"
            )

        self._status = IntegrationStatus.IN_PROGRESS
        self._started_at = datetime.now()

        # Emite evento
        from ..events.hubsoft_events import IntegrationStarted
        self.add_domain_event(IntegrationStarted(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            priority=self._priority.value,
            attempt_number=self.attempt_count + 1
        ))

    def record_attempt(
        self,
        success: bool,
        error_message: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """
        Registra uma tentativa de integração.

        Args:
            success: Se a tentativa foi bem-sucedida
            error_message: Mensagem de erro (se aplicável)
            response_data: Dados de resposta
            duration_ms: Duração em milissegundos
        """
        attempt = IntegrationAttempt(
            attempted_at=datetime.now(),
            success=success,
            error_message=error_message,
            response_data=response_data,
            duration_ms=duration_ms
        )

        self._attempts.append(attempt)

        # Emite evento de tentativa
        from ..events.hubsoft_events import IntegrationAttemptMade
        self.add_domain_event(IntegrationAttemptMade(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            attempt_number=len(self._attempts),
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        ))

        if success:
            self._complete_with_success(response_data)
        else:
            self._handle_failure(error_message, response_data)

    def complete_with_success(self, response_data: Dict[str, Any]) -> None:
        """
        Completa integração com sucesso.

        Args:
            response_data: Dados de resposta do HubSoft
        """
        if self._status != IntegrationStatus.IN_PROGRESS:
            raise IntegrationBusinessRuleError(
                f"Não é possível completar integração com status {self._status.value}"
            )

        self._status = IntegrationStatus.COMPLETED
        self._completed_at = datetime.now()
        self._hubsoft_response = response_data

        # Emite evento de sucesso
        from ..events.hubsoft_events import IntegrationCompleted
        self.add_domain_event(IntegrationCompleted(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            priority=self._priority.value,
            success=True,
            total_attempts=self.attempt_count,
            duration_seconds=self._calculate_total_duration(),
            response_data=response_data
        ))

    def fail_integration(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        is_retryable: bool = False
    ) -> None:
        """
        Falha a integração.

        Args:
            error_message: Mensagem de erro
            error_details: Detalhes do erro
            is_retryable: Se pode ser retentado
        """
        if is_retryable and self.can_retry():
            self._status = IntegrationStatus.RETRY_SCHEDULED
            retry_delay = self.get_retry_delay()

            # Emite evento de retry agendado
            from ..events.hubsoft_events import IntegrationRetryScheduled
            self.add_domain_event(IntegrationRetryScheduled(
                integration_id=self.id,
                integration_type=self._integration_type.value,
                attempt_number=self.attempt_count,
                retry_delay_seconds=retry_delay,
                error_message=error_message
            ))
        else:
            self._status = IntegrationStatus.FAILED
            self._completed_at = datetime.now()
            self._error_details = error_details or {}

            # Emite evento de falha
            from ..events.hubsoft_events import IntegrationFailed
            self.add_domain_event(IntegrationFailed(
                integration_id=self.id,
                integration_type=self._integration_type.value,
                priority=self._priority.value,
                total_attempts=self.attempt_count,
                final_error=error_message,
                error_details=error_details
            ))

    def cancel_integration(self, reason: str = "Cancelado pelo usuário") -> None:
        """
        Cancela a integração.

        Args:
            reason: Motivo do cancelamento
        """
        if self._status in (IntegrationStatus.COMPLETED, IntegrationStatus.FAILED):
            raise IntegrationBusinessRuleError("Não é possível cancelar integração finalizada")

        self._status = IntegrationStatus.CANCELLED
        self._completed_at = datetime.now()

        # Emite evento de cancelamento
        from ..events.hubsoft_events import IntegrationCancelled
        self.add_domain_event(IntegrationCancelled(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            reason=reason,
            attempts_made=self.attempt_count
        ))

    def update_priority(self, new_priority: IntegrationPriority, reason: str) -> None:
        """
        Atualiza prioridade da integração.

        Args:
            new_priority: Nova prioridade
            reason: Motivo da mudança
        """
        if self._status in (IntegrationStatus.COMPLETED, IntegrationStatus.FAILED, IntegrationStatus.CANCELLED):
            raise IntegrationBusinessRuleError("Não é possível alterar prioridade de integração finalizada")

        old_priority = self._priority
        self._priority = new_priority

        # Emite evento de mudança de prioridade
        from ..events.hubsoft_events import IntegrationPriorityChanged
        self.add_domain_event(IntegrationPriorityChanged(
            integration_id=self.id,
            integration_type=self._integration_type.value,
            old_priority=old_priority.value,
            new_priority=new_priority.value,
            reason=reason
        ))

    def add_metadata(self, key: str, value: Any) -> None:
        """Adiciona metadados à integração."""
        self._metadata[key] = value

    def get_execution_summary(self) -> Dict[str, Any]:
        """Retorna resumo da execução."""
        return {
            "integration_id": str(self.id),
            "type": self._integration_type.value,
            "status": self._status.value,
            "priority": self._priority.value,
            "attempts": self.attempt_count,
            "max_retries": self._max_retries,
            "can_retry": self.can_retry(),
            "scheduled_at": self._scheduled_at.isoformat() if self._scheduled_at else None,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
            "total_duration": self._calculate_total_duration(),
            "success_rate": self._calculate_success_rate(),
            "last_error": self._get_last_error()
        }

    # Métodos privados
    def _complete_with_success(self, response_data: Optional[Dict[str, Any]]) -> None:
        """Lógica interna para completar com sucesso."""
        self.complete_with_success(response_data or {})

    def _handle_failure(self, error_message: Optional[str], error_details: Optional[Dict[str, Any]]) -> None:
        """Lógica interna para tratar falhas."""
        error_msg = error_message or "Erro desconhecido"

        # Determina se erro é retentável
        is_retryable = self._is_retryable_error(error_msg, error_details)

        self.fail_integration(error_msg, error_details, is_retryable)

    def _is_retryable_error(self, error_message: str, error_details: Optional[Dict[str, Any]]) -> bool:
        """Determina se erro pode ser retentado."""
        retryable_patterns = ["timeout", "connection", "rate limit", "server error", "503", "502", "504"]
        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in retryable_patterns)

    def _calculate_total_duration(self) -> Optional[int]:
        """Calcula duração total em segundos."""
        if self._started_at and self._completed_at:
            return int((self._completed_at - self._started_at).total_seconds())
        return None

    def _calculate_success_rate(self) -> float:
        """Calcula taxa de sucesso das tentativas."""
        if not self._attempts:
            return 0.0
        successful = sum(1 for attempt in self._attempts if attempt.success)
        return (successful / len(self._attempts)) * 100

    def _get_last_error(self) -> Optional[str]:
        """Retorna último erro registrado."""
        failed_attempts = [a for a in self._attempts if not a.success]
        return failed_attempts[-1].error_message if failed_attempts else None


class IntegrationBusinessRuleError(Exception):
    """Erro de regra de negócio para integrações."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}