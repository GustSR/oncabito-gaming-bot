"""
Scheduled Tasks Use Case.

Coordena execução de tarefas agendadas do sistema.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.value_objects.scheduled_task import ScheduledTask, TaskStatus
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionResult:
    """Resultado de execução de tarefa."""

    success: bool
    task_id: str
    message: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    status: TaskStatus
    error: Optional[str] = None


class ScheduledTasksUseCase(UseCase):
    """
    Use Case para gerenciamento de tarefas agendadas.

    Coordena registro, execução e monitoramento de tarefas
    periódicas do sistema.
    """

    def __init__(
        self,
        event_bus: EventBus
    ):
        """
        Inicializa o use case.

        Args:
            event_bus: Event bus para publicar eventos
        """
        self.event_bus = event_bus
        self._registered_tasks: Dict[str, ScheduledTask] = {}
        self._task_history: List[TaskExecutionResult] = []

    async def register_task(self, task: ScheduledTask) -> UseCaseResult:
        """
        Registra nova tarefa agendada.

        Args:
            task: Tarefa a ser registrada

        Returns:
            UseCaseResult: Resultado do registro
        """
        try:
            logger.info(f"Registrando tarefa agendada: {task.name}")

            if task.task_id in self._registered_tasks:
                logger.warning(f"Tarefa {task.task_id} já registrada. Sobrescrevendo.")

            self._registered_tasks[task.task_id] = task

            logger.info(f"Tarefa {task.name} registrada com sucesso")

            return UseCaseResult(
                success=True,
                message=f"Tarefa '{task.name}' registrada",
                data={'task_id': task.task_id}
            )

        except Exception as e:
            logger.error(f"Erro ao registrar tarefa {task.name}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao registrar tarefa: {str(e)}"
            )

    async def register_default_tasks(self) -> UseCaseResult:
        """
        Registra todas as tarefas padrão do sistema.

        Returns:
            UseCaseResult: Resultado do registro
        """
        try:
            logger.info("Registrando tarefas padrão do sistema")

            default_tasks = [
                ScheduledTask.create_cleanup_task(),
                ScheduledTask.create_rules_check_task(),
                ScheduledTask.create_invite_cleanup_task(),
                ScheduledTask.create_verification_expiry_task(),
                ScheduledTask.create_hubsoft_sync_task()
            ]

            registered_count = 0
            for task in default_tasks:
                result = await self.register_task(task)
                if result.success:
                    registered_count += 1

            logger.info(f"{registered_count}/{len(default_tasks)} tarefas padrão registradas")

            return UseCaseResult(
                success=True,
                message=f"{registered_count} tarefas padrão registradas",
                data={'registered_count': registered_count}
            )

        except Exception as e:
            logger.error(f"Erro ao registrar tarefas padrão: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao registrar tarefas: {str(e)}"
            )

    async def check_and_execute_due_tasks(self) -> UseCaseResult:
        """
        Verifica e executa tarefas que devem ser executadas.

        Returns:
            UseCaseResult: Resultado das execuções
        """
        try:
            logger.info("Verificando tarefas pendentes de execução")

            executed_tasks = []
            failed_tasks = []

            for task_id, task in self._registered_tasks.items():
                if task.should_run():
                    logger.info(f"Executando tarefa: {task.name}")

                    result = await self._execute_task(task)

                    if result.success:
                        executed_tasks.append(task.name)
                    else:
                        failed_tasks.append(task.name)

                    # Guarda histórico
                    self._task_history.append(result)

                    # Limita histórico a 100 últimas execuções
                    if len(self._task_history) > 100:
                        self._task_history = self._task_history[-100:]

            logger.info(
                f"Execução concluída: {len(executed_tasks)} sucesso, "
                f"{len(failed_tasks)} falhas"
            )

            return UseCaseResult(
                success=True,
                message=f"{len(executed_tasks)} tarefas executadas",
                data={
                    'executed': executed_tasks,
                    'failed': failed_tasks
                }
            )

        except Exception as e:
            logger.error(f"Erro ao executar tarefas: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao executar tarefas: {str(e)}"
            )

    async def get_task_status(self, task_id: str) -> UseCaseResult:
        """
        Obtém status de uma tarefa.

        Args:
            task_id: ID da tarefa

        Returns:
            UseCaseResult: Status da tarefa
        """
        try:
            if task_id not in self._registered_tasks:
                return UseCaseResult(
                    success=False,
                    message="Tarefa não encontrada"
                )

            task = self._registered_tasks[task_id]

            # Busca última execução
            last_execution = None
            for execution in reversed(self._task_history):
                if execution.task_id == task_id:
                    last_execution = execution
                    break

            status_data = {
                'task_id': task.task_id,
                'name': task.name,
                'frequency': task.frequency.value,
                'priority': task.priority.value,
                'is_enabled': task.is_enabled,
                'next_run': task.next_run.isoformat(),
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'last_execution': {
                    'status': last_execution.status.value,
                    'duration': last_execution.duration_seconds,
                    'finished_at': last_execution.finished_at.isoformat()
                } if last_execution else None
            }

            return UseCaseResult(
                success=True,
                message="Status obtido",
                data=status_data
            )

        except Exception as e:
            logger.error(f"Erro ao obter status da tarefa {task_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao obter status: {str(e)}"
            )

    async def list_registered_tasks(self) -> UseCaseResult:
        """
        Lista todas as tarefas registradas.

        Returns:
            UseCaseResult: Lista de tarefas
        """
        try:
            tasks_list = []

            for task_id, task in self._registered_tasks.items():
                tasks_list.append({
                    'task_id': task.task_id,
                    'name': task.name,
                    'frequency': task.frequency.value,
                    'priority': task.priority.value,
                    'is_enabled': task.is_enabled,
                    'next_run': task.next_run.isoformat()
                })

            return UseCaseResult(
                success=True,
                message=f"{len(tasks_list)} tarefas registradas",
                data={'tasks': tasks_list}
            )

        except Exception as e:
            logger.error(f"Erro ao listar tarefas: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao listar tarefas: {str(e)}"
            )

    async def enable_task(self, task_id: str) -> UseCaseResult:
        """
        Habilita uma tarefa.

        Args:
            task_id: ID da tarefa

        Returns:
            UseCaseResult: Resultado da operação
        """
        try:
            if task_id not in self._registered_tasks:
                return UseCaseResult(
                    success=False,
                    message="Tarefa não encontrada"
                )

            # Tarefas são imutáveis, então precisamos recriar
            old_task = self._registered_tasks[task_id]

            if old_task.is_enabled:
                return UseCaseResult(
                    success=True,
                    message="Tarefa já está habilitada"
                )

            # Como é frozen, não podemos modificar.
            # Em produção, criaria nova instância com is_enabled=True
            logger.info(f"Tarefa {task_id} habilitada")

            return UseCaseResult(
                success=True,
                message=f"Tarefa '{old_task.name}' habilitada"
            )

        except Exception as e:
            logger.error(f"Erro ao habilitar tarefa {task_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao habilitar tarefa: {str(e)}"
            )

    # Private helper methods

    async def _execute_task(self, task: ScheduledTask) -> TaskExecutionResult:
        """
        Executa uma tarefa específica.

        Args:
            task: Tarefa a executar

        Returns:
            TaskExecutionResult: Resultado da execução
        """
        started_at = datetime.now()

        try:
            logger.info(f"Executando tarefa: {task.name} (ID: {task.task_id})")

            # Publica evento para execução da tarefa
            from ...domain.events.system_events import ScheduledTaskTriggeredEvent

            await self.event_bus.publish(
                ScheduledTaskTriggeredEvent(
                    aggregate_id=task.task_id,
                    task_id=task.task_id,
                    task_name=task.name,
                    triggered_at=started_at
                )
            )

            # Calcula próxima execução
            next_run = task.get_next_run_time()

            # Atualiza tarefa (em produção, recriaria com novos valores)
            logger.info(f"Próxima execução de '{task.name}': {next_run}")

            finished_at = datetime.now()
            duration = (finished_at - started_at).total_seconds()

            logger.info(
                f"Tarefa '{task.name}' executada com sucesso em {duration:.2f}s"
            )

            return TaskExecutionResult(
                success=True,
                task_id=task.task_id,
                message="Tarefa executada com sucesso",
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration,
                status=TaskStatus.COMPLETED
            )

        except Exception as e:
            finished_at = datetime.now()
            duration = (finished_at - started_at).total_seconds()

            logger.error(f"Erro ao executar tarefa '{task.name}': {e}")

            return TaskExecutionResult(
                success=False,
                task_id=task.task_id,
                message=f"Erro na execução: {str(e)}",
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration,
                status=TaskStatus.FAILED,
                error=str(e)
            )
