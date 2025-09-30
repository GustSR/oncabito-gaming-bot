"""
Domain Events relacionados ao sistema.

Define os eventos que são disparados quando
operações do sistema ocorrem.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent


@dataclass(frozen=True)
class ScheduledTaskTriggeredEvent(DomainEvent):
    """
    Evento disparado quando tarefa agendada é acionada.

    Attributes:
        task_id: ID da tarefa
        task_name: Nome da tarefa
        triggered_at: Data/hora do acionamento
    """
    task_id: str
    task_name: str
    triggered_at: datetime


@dataclass(frozen=True)
class ScheduledTaskCompletedEvent(DomainEvent):
    """
    Evento disparado quando tarefa agendada é concluída.

    Attributes:
        task_id: ID da tarefa
        task_name: Nome da tarefa
        duration_seconds: Duração da execução
        completed_at: Data/hora da conclusão
    """
    task_id: str
    task_name: str
    duration_seconds: float
    completed_at: datetime


@dataclass(frozen=True)
class ScheduledTaskFailedEvent(DomainEvent):
    """
    Evento disparado quando tarefa agendada falha.

    Attributes:
        task_id: ID da tarefa
        task_name: Nome da tarefa
        error: Mensagem de erro
        failed_at: Data/hora da falha
        retry_count: Número de tentativas
    """
    task_id: str
    task_name: str
    error: str
    failed_at: datetime
    retry_count: int


@dataclass(frozen=True)
class SystemHealthCheckEvent(DomainEvent):
    """
    Evento disparado durante health check do sistema.

    Attributes:
        status: Status do sistema (healthy, degraded, unhealthy)
        checked_at: Data/hora da verificação
        details: Detalhes adicionais
    """
    status: str
    checked_at: datetime
    details: Optional[dict] = None


@dataclass(frozen=True)
class SystemStartedEvent(DomainEvent):
    """
    Evento disparado quando sistema é iniciado.

    Attributes:
        version: Versão do sistema
        started_at: Data/hora da inicialização
        config: Configurações carregadas
    """
    version: str
    started_at: datetime
    config: Optional[dict] = None


@dataclass(frozen=True)
class SystemShutdownEvent(DomainEvent):
    """
    Evento disparado quando sistema é encerrado.

    Attributes:
        reason: Motivo do encerramento
        shutdown_at: Data/hora do encerramento
        graceful: Se foi encerramento gracioso
    """
    reason: str
    shutdown_at: datetime
    graceful: bool
