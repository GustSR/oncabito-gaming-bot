"""
Scheduled Task Value Object.

Representa tarefas agendadas do sistema.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum


class TaskFrequency(Enum):
    """Frequência de execução de tarefas."""

    ONCE = "once"                # Uma vez apenas
    HOURLY = "hourly"           # A cada hora
    DAILY = "daily"             # Diariamente
    WEEKLY = "weekly"           # Semanalmente
    CUSTOM = "custom"           # Intervalo customizado


class TaskPriority(Enum):
    """Prioridade de execução."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Status da tarefa."""

    PENDING = "pending"         # Aguardando execução
    RUNNING = "running"         # Em execução
    COMPLETED = "completed"     # Concluída
    FAILED = "failed"          # Falhou
    CANCELLED = "cancelled"     # Cancelada


@dataclass(frozen=True)
class ScheduledTask:
    """
    Value Object representando tarefa agendada.

    Attributes:
        task_id: ID único da tarefa
        name: Nome descritivo
        description: Descrição da tarefa
        frequency: Frequência de execução
        priority: Prioridade
        next_run: Próxima execução
        last_run: Última execução (opcional)
        retry_count: Número de tentativas em caso de falha
        max_retries: Máximo de tentativas
        timeout_seconds: Timeout em segundos
        is_enabled: Se tarefa está habilitada
    """

    task_id: str
    name: str
    description: str
    frequency: TaskFrequency
    priority: TaskPriority
    next_run: datetime
    last_run: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300  # 5 minutos padrão
    is_enabled: bool = True

    def should_run(self) -> bool:
        """
        Verifica se tarefa deve ser executada.

        Returns:
            bool: True se deve executar
        """
        if not self.is_enabled:
            return False

        return datetime.now() >= self.next_run

    def can_retry(self) -> bool:
        """
        Verifica se pode tentar novamente.

        Returns:
            bool: True se pode retentar
        """
        return self.retry_count < self.max_retries

    def get_next_run_time(self) -> datetime:
        """
        Calcula próximo horário de execução.

        Returns:
            datetime: Próxima execução
        """
        base_time = self.last_run or datetime.now()

        if self.frequency == TaskFrequency.HOURLY:
            return base_time + timedelta(hours=1)
        elif self.frequency == TaskFrequency.DAILY:
            return base_time + timedelta(days=1)
        elif self.frequency == TaskFrequency.WEEKLY:
            return base_time + timedelta(weeks=1)
        elif self.frequency == TaskFrequency.ONCE:
            # Tarefas únicas não se repetem
            return datetime.max
        else:
            # Custom - retorna próxima hora por padrão
            return base_time + timedelta(hours=1)

    @staticmethod
    def create_cleanup_task() -> 'ScheduledTask':
        """
        Cria tarefa de limpeza de membros inativos.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="cleanup_inactive_members",
            name="Limpeza de Membros Inativos",
            description="Remove membros sem contrato ativo do grupo",
            frequency=TaskFrequency.DAILY,
            priority=TaskPriority.HIGH,
            next_run=datetime.now() + timedelta(hours=1),
            timeout_seconds=600  # 10 minutos
        )

    @staticmethod
    def create_rules_check_task() -> 'ScheduledTask':
        """
        Cria tarefa de verificação de regras expiradas.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="check_expired_rules",
            name="Verificação de Regras Expiradas",
            description="Remove membros que não aceitaram regras em 24h",
            frequency=TaskFrequency.HOURLY,
            priority=TaskPriority.CRITICAL,
            next_run=datetime.now() + timedelta(minutes=30),
            timeout_seconds=300
        )

    @staticmethod
    def create_invite_cleanup_task() -> 'ScheduledTask':
        """
        Cria tarefa de limpeza de convites expirados.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="cleanup_expired_invites",
            name="Limpeza de Convites Expirados",
            description="Revoga links de convite expirados",
            frequency=TaskFrequency.HOURLY,
            priority=TaskPriority.NORMAL,
            next_run=datetime.now() + timedelta(minutes=15),
            timeout_seconds=180
        )

    @staticmethod
    def create_verification_expiry_task() -> 'ScheduledTask':
        """
        Cria tarefa de expiração de verificações de CPF.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="expire_old_verifications",
            name="Expiração de Verificações Antigas",
            description="Marca verificações de CPF antigas como expiradas",
            frequency=TaskFrequency.DAILY,
            priority=TaskPriority.NORMAL,
            next_run=datetime.now() + timedelta(hours=2),
            timeout_seconds=300
        )

    @staticmethod
    def create_hubsoft_sync_task() -> 'ScheduledTask':
        """
        Cria tarefa de sincronização com HubSoft.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="sync_hubsoft_contracts",
            name="Sincronização HubSoft",
            description="Sincroniza status de contratos com HubSoft API",
            frequency=TaskFrequency.DAILY,
            priority=TaskPriority.HIGH,
            next_run=datetime.now() + timedelta(hours=1),
            timeout_seconds=900  # 15 minutos
        )

    @staticmethod
    def create_member_cpf_check_task() -> 'ScheduledTask':
        """
        Cria tarefa de verificação de CPF de membros do grupo.

        Verifica diariamente se todos os membros (exceto admins) têm CPF vinculado.
        Remove membros sem CPF após 24h de notificação.

        Returns:
            ScheduledTask: Tarefa configurada
        """
        return ScheduledTask(
            task_id="check_member_cpf_daily",
            name="Verificação de CPF de Membros",
            description="Verifica e remove membros sem CPF vinculado",
            frequency=TaskFrequency.DAILY,
            priority=TaskPriority.HIGH,
            next_run=datetime.now() + timedelta(hours=2),
            timeout_seconds=600  # 10 minutos
        )
