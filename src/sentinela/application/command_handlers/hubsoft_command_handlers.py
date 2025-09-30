"""
HubSoft Integration Command Handlers.

Implementa handlers para processar comandos de integração com HubSoft,
gerenciando todo o ciclo de vida das operações de sincronização.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..commands.hubsoft_commands import (
    ScheduleHubSoftIntegrationCommand,
    SyncTicketToHubSoftCommand,
    VerifyUserInHubSoftCommand,
    FetchClientDataFromHubSoftCommand,
    UpdateTicketStatusInHubSoftCommand,
    BulkSyncTicketsToHubSoftCommand,
    RetryFailedIntegrationsCommand,
    CancelHubSoftIntegrationCommand,
    UpdateIntegrationPriorityCommand,
    GetHubSoftIntegrationStatusCommand
)
from .base import CommandHandler, CommandResult
from ...domain.entities.hubsoft_integration import (
    HubSoftIntegrationRequest,
    IntegrationId,
    IntegrationType,
    IntegrationPriority,
    IntegrationStatus
)
from ...domain.repositories.hubsoft_repository import HubSoftIntegrationRepository
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ScheduleHubSoftIntegrationHandler(CommandHandler[ScheduleHubSoftIntegrationCommand]):
    """Handler para agendar integrações com HubSoft."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: ScheduleHubSoftIntegrationCommand) -> CommandResult:
        try:
            # Valida tipo de integração
            try:
                integration_type = IntegrationType(command.integration_type)
            except ValueError:
                return CommandResult.failure(
                    "INVALID_INTEGRATION_TYPE",
                    f"Tipo de integração inválido: {command.integration_type}"
                )

            # Valida prioridade
            try:
                priority = IntegrationPriority(command.priority)
            except ValueError:
                return CommandResult.failure(
                    "INVALID_PRIORITY",
                    f"Prioridade inválida: {command.priority}"
                )

            # Cria nova integração
            integration_id = IntegrationId.generate()
            integration = HubSoftIntegrationRequest(
                integration_id=integration_id,
                integration_type=integration_type,
                priority=priority,
                payload=command.payload,
                metadata=command.metadata,
                max_retries=command.max_retries,
                timeout_seconds=command.timeout_seconds
            )

            # Agenda para execução
            integration.schedule_integration(command.scheduled_at)

            # Salva no repositório
            await self.integration_repository.save(integration)

            # Publica eventos
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Integração {integration_id.value} agendada com sucesso")

            return CommandResult.success(
                data={
                    "integration_id": integration_id.value,
                    "type": integration_type.value,
                    "priority": priority.value,
                    "scheduled_at": (command.scheduled_at or datetime.now()).isoformat()
                },
                message="Integração agendada com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao agendar integração: {e}")
            return CommandResult.failure(
                "SCHEDULE_ERROR",
                f"Erro ao agendar integração: {str(e)}"
            )


class SyncTicketToHubSoftHandler(CommandHandler[SyncTicketToHubSoftCommand]):
    """Handler para sincronizar tickets com HubSoft."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: SyncTicketToHubSoftCommand) -> CommandResult:
        try:
            # Monta payload da sincronização
            payload = {
                "ticket_id": command.ticket_id,
                "sync_type": command.sync_type,
                "hubsoft_ticket_id": command.hubsoft_ticket_id,
                "force_sync": command.force_sync
            }

            # Determina prioridade
            priority = IntegrationPriority(command.priority)

            # Cria integração
            integration_id = IntegrationId.generate()
            integration = HubSoftIntegrationRequest(
                integration_id=integration_id,
                integration_type=IntegrationType.TICKET_SYNC,
                priority=priority,
                payload=payload,
                metadata={
                    "ticket_id": command.ticket_id,
                    "sync_type": command.sync_type
                }
            )

            # Agenda para execução imediata
            integration.schedule_integration()

            # Salva e publica eventos
            await self.integration_repository.save(integration)
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Sincronização de ticket {command.ticket_id} agendada")

            return CommandResult.success(
                data={
                    "integration_id": integration_id.value,
                    "ticket_id": command.ticket_id,
                    "sync_type": command.sync_type
                },
                message="Sincronização de ticket agendada"
            )

        except Exception as e:
            logger.error(f"Erro ao agendar sincronização: {e}")
            return CommandResult.failure(
                "SYNC_ERROR",
                f"Erro ao agendar sincronização: {str(e)}"
            )


class VerifyUserInHubSoftHandler(CommandHandler[VerifyUserInHubSoftCommand]):
    """Handler para verificar usuário no HubSoft."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: VerifyUserInHubSoftCommand) -> CommandResult:
        try:
            # Monta payload da verificação
            payload = {
                "user_id": command.user_id,
                "cpf": command.cpf,
                "cache_duration": command.cache_duration,
                "force_refresh": command.force_refresh,
                "include_contracts": command.include_contracts
            }

            # Cria integração de verificação
            integration_id = IntegrationId.generate()
            integration = HubSoftIntegrationRequest(
                integration_id=integration_id,
                integration_type=IntegrationType.USER_VERIFICATION,
                priority=IntegrationPriority.HIGH,  # Verificações são alta prioridade
                payload=payload,
                metadata={
                    "user_id": command.user_id,
                    "cpf_masked": command.cpf[:3] + "***" + command.cpf[-2:]
                }
            )

            # Agenda para execução
            integration.schedule_integration()

            # Salva e publica eventos
            await self.integration_repository.save(integration)
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Verificação de usuário {command.user_id} agendada")

            return CommandResult.success(
                data={
                    "integration_id": integration_id.value,
                    "user_id": command.user_id
                },
                message="Verificação de usuário agendada"
            )

        except Exception as e:
            logger.error(f"Erro ao agendar verificação: {e}")
            return CommandResult.failure(
                "VERIFICATION_ERROR",
                f"Erro ao agendar verificação: {str(e)}"
            )


class BulkSyncTicketsToHubSoftHandler(CommandHandler[BulkSyncTicketsToHubSoftCommand]):
    """Handler para sincronização em lote de tickets."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: BulkSyncTicketsToHubSoftCommand) -> CommandResult:
        try:
            # Valida entrada
            if not command.ticket_ids:
                return CommandResult.failure(
                    "EMPTY_TICKET_LIST",
                    "Lista de tickets não pode estar vazia"
                )

            # Monta payload da sincronização em lote
            payload = {
                "ticket_ids": command.ticket_ids,
                "sync_type": command.sync_type,
                "batch_size": command.batch_size,
                "delay_between_batches": command.delay_between_batches
            }

            # Cria integração em lote
            integration_id = IntegrationId.generate()
            integration = HubSoftIntegrationRequest(
                integration_id=integration_id,
                integration_type=IntegrationType.BULK_SYNC,
                priority=IntegrationPriority(command.priority),
                payload=payload,
                metadata={
                    "total_tickets": len(command.ticket_ids),
                    "batch_count": (len(command.ticket_ids) + command.batch_size - 1) // command.batch_size
                },
                timeout_seconds=command.batch_size * 30  # Timeout baseado no tamanho do lote
            )

            # Agenda para execução
            integration.schedule_integration()

            # Salva e publica eventos
            await self.integration_repository.save(integration)
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Sincronização em lote de {len(command.ticket_ids)} tickets agendada")

            return CommandResult.success(
                data={
                    "integration_id": integration_id.value,
                    "total_tickets": len(command.ticket_ids),
                    "batch_size": command.batch_size
                },
                message=f"Sincronização em lote de {len(command.ticket_ids)} tickets agendada"
            )

        except Exception as e:
            logger.error(f"Erro ao agendar sincronização em lote: {e}")
            return CommandResult.failure(
                "BULK_SYNC_ERROR",
                f"Erro ao agendar sincronização em lote: {str(e)}"
            )


class RetryFailedIntegrationsHandler(CommandHandler[RetryFailedIntegrationsCommand]):
    """Handler para retentar integrações falhadas."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: RetryFailedIntegrationsCommand) -> CommandResult:
        try:
            # Define critérios de busca
            max_age = datetime.now() - timedelta(hours=command.max_age_hours)

            # Busca integrações falhadas
            failed_integrations = await self.integration_repository.find_failed_integrations(
                integration_type=command.integration_type,
                since=max_age,
                limit=command.limit
            )

            retried_count = 0
            for integration in failed_integrations:
                try:
                    # Verifica se pode fazer retry
                    if integration.can_retry() or command.force_retry:
                        # Reagenda integração
                        integration.schedule_integration()

                        # Salva
                        await self.integration_repository.save(integration)

                        # Publica eventos
                        for event in integration.get_domain_events():
                            await self.event_bus.publish(event)

                        retried_count += 1

                except Exception as e:
                    logger.error(f"Erro ao retentar integração {integration.id}: {e}")
                    continue

            logger.info(f"Retentou {retried_count} integrações falhadas")

            return CommandResult.success(
                data={
                    "retried_count": retried_count,
                    "total_found": len(failed_integrations)
                },
                message=f"Retentou {retried_count} integrações falhadas"
            )

        except Exception as e:
            logger.error(f"Erro ao retentar integrações: {e}")
            return CommandResult.failure(
                "RETRY_ERROR",
                f"Erro ao retentar integrações: {str(e)}"
            )


class CancelHubSoftIntegrationHandler(CommandHandler[CancelHubSoftIntegrationCommand]):
    """Handler para cancelar integrações."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: CancelHubSoftIntegrationCommand) -> CommandResult:
        try:
            # Busca integração
            integration_id = IntegrationId(command.integration_id)
            integration = await self.integration_repository.find_by_id(integration_id)

            if not integration:
                return CommandResult.failure(
                    "INTEGRATION_NOT_FOUND",
                    f"Integração {command.integration_id} não encontrada"
                )

            # Cancela integração
            integration.cancel_integration(command.reason)

            # Salva e publica eventos
            await self.integration_repository.save(integration)
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Integração {command.integration_id} cancelada")

            return CommandResult.success(
                data={
                    "integration_id": command.integration_id,
                    "reason": command.reason
                },
                message="Integração cancelada com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao cancelar integração: {e}")
            return CommandResult.failure(
                "CANCEL_ERROR",
                f"Erro ao cancelar integração: {str(e)}"
            )


class UpdateIntegrationPriorityHandler(CommandHandler[UpdateIntegrationPriorityCommand]):
    """Handler para atualizar prioridade de integração."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        event_bus: EventBus
    ):
        self.integration_repository = integration_repository
        self.event_bus = event_bus

    async def handle(self, command: UpdateIntegrationPriorityCommand) -> CommandResult:
        try:
            # Busca integração
            integration_id = IntegrationId(command.integration_id)
            integration = await self.integration_repository.find_by_id(integration_id)

            if not integration:
                return CommandResult.failure(
                    "INTEGRATION_NOT_FOUND",
                    f"Integração {command.integration_id} não encontrada"
                )

            # Valida nova prioridade
            try:
                new_priority = IntegrationPriority(command.new_priority)
            except ValueError:
                return CommandResult.failure(
                    "INVALID_PRIORITY",
                    f"Prioridade inválida: {command.new_priority}"
                )

            # Atualiza prioridade
            integration.update_priority(new_priority, command.reason)

            # Salva e publica eventos
            await self.integration_repository.save(integration)
            for event in integration.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Prioridade da integração {command.integration_id} atualizada")

            return CommandResult.success(
                data={
                    "integration_id": command.integration_id,
                    "new_priority": command.new_priority,
                    "reason": command.reason
                },
                message="Prioridade atualizada com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar prioridade: {e}")
            return CommandResult.failure(
                "UPDATE_PRIORITY_ERROR",
                f"Erro ao atualizar prioridade: {str(e)}"
            )


class GetHubSoftIntegrationStatusHandler(CommandHandler[GetHubSoftIntegrationStatusCommand]):
    """Handler para obter status de integrações."""

    def __init__(self, integration_repository: HubSoftIntegrationRepository):
        self.integration_repository = integration_repository

    async def handle(self, command: GetHubSoftIntegrationStatusCommand) -> CommandResult:
        try:
            if command.integration_id:
                # Busca integração específica
                integration_id = IntegrationId(command.integration_id)
                integration = await self.integration_repository.find_by_id(integration_id)

                if not integration:
                    return CommandResult.failure(
                        "INTEGRATION_NOT_FOUND",
                        f"Integração {command.integration_id} não encontrada"
                    )

                # Monta dados da integração
                data = integration.get_execution_summary()

                if command.include_attempts:
                    data["attempts"] = [
                        {
                            "attempted_at": attempt.attempted_at.isoformat(),
                            "success": attempt.success,
                            "error_message": attempt.error_message,
                            "duration_ms": attempt.duration_ms
                        }
                        for attempt in integration.attempts
                    ]

                if command.include_payload:
                    data["payload"] = integration.payload
                    data["metadata"] = integration.metadata

                return CommandResult.success(
                    data=data,
                    message="Status da integração obtido"
                )
            else:
                # Busca integrações ativas
                active_integrations = await self.integration_repository.find_active_integrations()

                integrations_data = []
                for integration in active_integrations:
                    integration_data = {
                        "integration_id": integration.id.value,
                        "type": integration.integration_type.value,
                        "status": integration.status.value,
                        "priority": integration.priority.value,
                        "scheduled_at": integration.scheduled_at.isoformat() if integration.scheduled_at else None,
                        "attempts": integration.attempt_count
                    }
                    integrations_data.append(integration_data)

                return CommandResult.success(
                    data={
                        "total": len(integrations_data),
                        "integrations": integrations_data
                    },
                    message=f"Encontradas {len(integrations_data)} integrações ativas"
                )

        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return CommandResult.failure(
                "STATUS_ERROR",
                f"Erro ao obter status: {str(e)}"
            )