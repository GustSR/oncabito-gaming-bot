"""
HubSoft Integration Event Handlers.

Processa eventos relacionados às integrações com HubSoft,
incluindo execução de integrações e sincronização de dados.
"""

import logging
import asyncio
from typing import Dict, Any

from .event_bus import EventHandler
from ...domain.events.hubsoft_events import (
    IntegrationScheduled,
    IntegrationStarted,
    IntegrationAttemptMade,
    IntegrationCompleted,
    IntegrationFailed,
    IntegrationRetryScheduled,
    IntegrationCancelled,
    IntegrationPriorityChanged,
    HubSoftTicketSynced,
    HubSoftUserDataFetched,
    HubSoftRateLimitHit,
    HubSoftConnectionRestored,
    HubSoftBulkSyncCompleted
)
from ...domain.entities.hubsoft_integration import IntegrationId, IntegrationType
from ...domain.repositories.hubsoft_repository import (
    HubSoftIntegrationRepository,
    HubSoftAPIRepository,
    HubSoftCacheRepository,
    HubSoftAPIError
)

logger = logging.getLogger(__name__)


class IntegrationScheduledHandler(EventHandler[IntegrationScheduled]):
    """Processa eventos de integração agendada."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository
    ):
        self.integration_repository = integration_repository

    async def handle(self, event: IntegrationScheduled) -> None:
        try:
            logger.info(
                f"Integração {event.integration_id.value} agendada: "
                f"tipo={event.integration_type}, prioridade={event.priority}"
            )

            # Log para monitoramento
            logger.debug(f"Integration scheduled: {event.integration_id.value}")

        except Exception as e:
            logger.error(f"Erro ao processar evento IntegrationScheduled: {e}")


class IntegrationStartedHandler(EventHandler[IntegrationStarted]):
    """Processa eventos de início de integração."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository,
        api_repository: HubSoftAPIRepository,
        cache_repository: HubSoftCacheRepository
    ):
        self.integration_repository = integration_repository
        self.api_repository = api_repository
        self.cache_repository = cache_repository

    async def handle(self, event: IntegrationStarted) -> None:
        try:
            logger.info(
                f"Iniciando integração {event.integration_id.value}: "
                f"tipo={event.integration_type}, tentativa={event.attempt_number}"
            )

            # Busca integração
            integration = await self.integration_repository.find_by_id(event.integration_id)
            if not integration:
                logger.error(f"Integração {event.integration_id.value} não encontrada")
                return

            # Executa integração de acordo com o tipo
            await self._execute_integration(integration, event)

        except Exception as e:
            logger.error(f"Erro ao processar evento IntegrationStarted: {e}")

    async def _execute_integration(self, integration, event: IntegrationStarted) -> None:
        """Executa a integração baseada no tipo."""

        integration_type = IntegrationType(event.integration_type)

        try:
            if integration_type == IntegrationType.TICKET_SYNC:
                await self._execute_ticket_sync(integration)
            elif integration_type == IntegrationType.USER_VERIFICATION:
                await self._execute_user_verification(integration)
            elif integration_type == IntegrationType.CLIENT_DATA_FETCH:
                await self._execute_client_data_fetch(integration)
            elif integration_type == IntegrationType.STATUS_UPDATE:
                await self._execute_status_update(integration)
            elif integration_type == IntegrationType.BULK_SYNC:
                await self._execute_bulk_sync(integration)
            else:
                raise ValueError(f"Tipo de integração não suportado: {integration_type}")

        except Exception as e:
            # Registra falha na integração
            error_message = str(e)
            is_retryable = isinstance(e, HubSoftAPIError) and e.is_retryable()

            integration.fail_integration(
                error_message=error_message,
                error_details={"exception_type": type(e).__name__},
                is_retryable=is_retryable
            )

            await self.integration_repository.save(integration)

    async def _execute_ticket_sync(self, integration) -> None:
        """Executa sincronização de ticket."""
        payload = integration.payload
        ticket_id = payload.get("ticket_id")
        sync_type = payload.get("sync_type")
        hubsoft_ticket_id = payload.get("hubsoft_ticket_id")

        logger.info(f"Sincronizando ticket {ticket_id}: {sync_type}")

        if sync_type == "create":
            # Criar ticket no HubSoft
            ticket_data = await self._prepare_ticket_data(ticket_id)
            result = await self.api_repository.create_ticket(ticket_data)

        elif sync_type == "update":
            # Atualizar ticket existente
            updates = await self._prepare_ticket_updates(ticket_id)
            result = await self.api_repository.update_ticket(hubsoft_ticket_id, updates)

        elif sync_type == "status_change":
            # Atualizar apenas status
            updates = {"status": payload.get("new_status")}
            result = await self.api_repository.update_ticket(hubsoft_ticket_id, updates)

        else:
            raise ValueError(f"Tipo de sincronização inválido: {sync_type}")

        # Marca como concluída
        integration.complete_with_success(result)
        await self.integration_repository.save(integration)

    async def _execute_user_verification(self, integration) -> None:
        """Executa verificação de usuário."""
        payload = integration.payload
        cpf = payload.get("cpf")
        user_id = payload.get("user_id")
        include_contracts = payload.get("include_contracts", True)

        logger.info(f"Verificando usuário {user_id} no HubSoft")

        # Verifica cache primeiro
        cached_data = await self.cache_repository.get_cached_client_data(cpf)
        if cached_data and not payload.get("force_refresh", False):
            result = cached_data
        else:
            # Busca na API
            result = await self.api_repository.verify_client_by_cpf(
                cpf, include_contracts
            )

            # Armazena no cache
            cache_duration = payload.get("cache_duration", 3600)
            await self.cache_repository.cache_client_data(
                cpf, result, cache_duration
            )

        # Marca como concluída
        integration.complete_with_success(result)
        await self.integration_repository.save(integration)

    async def _execute_client_data_fetch(self, integration) -> None:
        """Executa busca de dados de cliente."""
        payload = integration.payload
        cpf = payload.get("cpf")

        logger.info(f"Buscando dados de cliente: CPF={cpf[:3]}***{cpf[-2:]}")

        # Busca dados completos
        client_data = await self.api_repository.verify_client_by_cpf(
            cpf, payload.get("include_contracts", True)
        )

        # Busca tickets se solicitado
        if payload.get("include_tickets", True):
            tickets = await self.api_repository.search_tickets_by_cpf(cpf)
            client_data["tickets"] = tickets

        # Busca contratos se solicitado
        if payload.get("include_billing", False):
            contracts = await self.api_repository.get_client_contracts(cpf)
            client_data["contracts"] = contracts

        # Cache dos dados
        cache_duration = payload.get("cache_duration", 3600)
        await self.cache_repository.cache_client_data(
            cpf, client_data, cache_duration
        )

        # Marca como concluída
        integration.complete_with_success(client_data)
        await self.integration_repository.save(integration)

    async def _execute_status_update(self, integration) -> None:
        """Executa atualização de status."""
        payload = integration.payload
        hubsoft_ticket_id = payload.get("hubsoft_ticket_id")
        new_status = payload.get("new_status")

        logger.info(f"Atualizando status do ticket {hubsoft_ticket_id}: {new_status}")

        updates = {
            "status": new_status,
            "notes": payload.get("notes", "")
        }

        result = await self.api_repository.update_ticket(hubsoft_ticket_id, updates)

        # Marca como concluída
        integration.complete_with_success(result)
        await self.integration_repository.save(integration)

    async def _execute_bulk_sync(self, integration) -> None:
        """Executa sincronização em lote."""
        payload = integration.payload
        ticket_ids = payload.get("ticket_ids", [])
        batch_size = payload.get("batch_size", 10)
        delay_between_batches = payload.get("delay_between_batches", 5)

        logger.info(f"Sincronização em lote: {len(ticket_ids)} tickets")

        successful_count = 0
        failed_count = 0
        results = []

        # Processa em lotes
        for i in range(0, len(ticket_ids), batch_size):
            batch = ticket_ids[i:i + batch_size]

            # Processa lote atual
            batch_results = await self._process_ticket_batch(batch)
            results.extend(batch_results)

            # Conta sucessos e falhas
            for result in batch_results:
                if result.get("success", False):
                    successful_count += 1
                else:
                    failed_count += 1

            # Delay entre lotes (exceto no último)
            if i + batch_size < len(ticket_ids):
                await asyncio.sleep(delay_between_batches)

        # Resultado final
        final_result = {
            "total_tickets": len(ticket_ids),
            "successful": successful_count,
            "failed": failed_count,
            "results": results
        }

        # Marca como concluída
        integration.complete_with_success(final_result)
        await self.integration_repository.save(integration)

    async def _process_ticket_batch(self, ticket_ids) -> list:
        """Processa um lote de tickets."""
        tasks = []
        for ticket_id in ticket_ids:
            task = self._sync_single_ticket(ticket_id)
            tasks.append(task)

        # Executa em paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Processa resultados
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "ticket_id": ticket_ids[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    async def _sync_single_ticket(self, ticket_id) -> Dict[str, Any]:
        """Sincroniza um único ticket."""
        try:
            # Prepara dados do ticket
            ticket_data = await self._prepare_ticket_data(ticket_id)

            # Cria no HubSoft
            result = await self.api_repository.create_ticket(ticket_data)

            return {
                "ticket_id": ticket_id,
                "success": True,
                "hubsoft_ticket_id": result.get("id"),
                "data": result
            }

        except Exception as e:
            return {
                "ticket_id": ticket_id,
                "success": False,
                "error": str(e)
            }

    async def _prepare_ticket_data(self, ticket_id) -> Dict[str, Any]:
        """Prepara dados do ticket para envio ao HubSoft."""
        # Esta função seria implementada com base na estrutura dos dados
        # Por enquanto, retorna dados mock
        return {
            "id": ticket_id,
            "title": f"Ticket {ticket_id}",
            "description": "Ticket sincronizado automaticamente",
            "status": "open",
            "priority": "normal"
        }

    async def _prepare_ticket_updates(self, ticket_id) -> Dict[str, Any]:
        """Prepara atualizações do ticket."""
        # Esta função seria implementada com base nas mudanças necessárias
        return {
            "updated_at": "now",
            "notes": "Ticket atualizado via integração"
        }


class IntegrationFailedHandler(EventHandler[IntegrationFailed]):
    """Processa eventos de falha de integração."""

    def __init__(self):
        pass

    async def handle(self, event: IntegrationFailed) -> None:
        try:
            logger.error(
                f"Integração {event.integration_id.value} falhou: "
                f"tipo={event.integration_type}, "
                f"tentativas={event.total_attempts}, "
                f"erro={event.final_error}"
            )

            # Aqui poderíamos notificar administradores sobre falhas críticas
            if event.priority in ("high", "urgent"):
                logger.critical(f"Falha crítica na integração: {event.integration_id.value}")

        except Exception as e:
            logger.error(f"Erro ao processar evento IntegrationFailed: {e}")


class IntegrationRetryScheduledHandler(EventHandler[IntegrationRetryScheduled]):
    """Processa eventos de retry agendado."""

    def __init__(self):
        pass

    async def handle(self, event: IntegrationRetryScheduled) -> None:
        try:
            logger.warning(
                f"Retry agendado para integração {event.integration_id.value}: "
                f"tentativa={event.attempt_number}, "
                f"delay={event.retry_delay_seconds}s, "
                f"erro={event.error_message}"
            )

            # Log para monitoramento de retries
            logger.debug(f"Integration retry scheduled: {event.integration_id.value}")

        except Exception as e:
            logger.error(f"Erro ao processar evento IntegrationRetryScheduled: {e}")


class HubSoftRateLimitHitHandler(EventHandler[HubSoftRateLimitHit]):
    """Processa eventos de rate limit atingido."""

    def __init__(self):
        pass

    async def handle(self, event: HubSoftRateLimitHit) -> None:
        try:
            logger.warning(
                f"Rate limit atingido: tipo={event.integration_type}, "
                f"taxa={event.current_rate}/{event.limit_threshold}, "
                f"reset={event.reset_time}, "
                f"operações_afetadas={event.affected_operations}"
            )

            # Aqui poderíamos implementar lógica para pausar integrações
            # ou ajustar dinamicamente os rate limits

        except Exception as e:
            logger.error(f"Erro ao processar evento HubSoftRateLimitHit: {e}")


class HubSoftConnectionRestoredHandler(EventHandler[HubSoftConnectionRestored]):
    """Processa eventos de conexão restaurada."""

    def __init__(
        self,
        integration_repository: HubSoftIntegrationRepository
    ):
        self.integration_repository = integration_repository

    async def handle(self, event: HubSoftConnectionRestored) -> None:
        try:
            logger.info(
                f"Conexão HubSoft restaurada: "
                f"downtime={event.downtime_duration}s, "
                f"operações_pendentes={event.pending_operations}, "
                f"qualidade={event.connection_quality}"
            )

            # Aqui poderíamos reagendar integrações que falharam durante a indisponibilidade
            if event.pending_operations > 0:
                logger.info(f"Reagendando {event.pending_operations} operações pendentes")

        except Exception as e:
            logger.error(f"Erro ao processar evento HubSoftConnectionRestored: {e}")


class HubSoftBulkSyncCompletedHandler(EventHandler[HubSoftBulkSyncCompleted]):
    """Processa eventos de sincronização em lote completada."""

    def __init__(self):
        pass

    async def handle(self, event: HubSoftBulkSyncCompleted) -> None:
        try:
            success_rate = (event.successful_items / event.total_items) * 100

            logger.info(
                f"Sincronização em lote completada: "
                f"lote={event.sync_batch_id}, "
                f"tipo={event.sync_type}, "
                f"total={event.total_items}, "
                f"sucessos={event.successful_items}, "
                f"falhas={event.failed_items}, "
                f"taxa_sucesso={success_rate:.1f}%, "
                f"duração={event.duration_seconds}s"
            )

            # Alerta se taxa de sucesso for baixa
            if success_rate < 80:
                logger.warning(f"Taxa de sucesso baixa na sincronização: {success_rate:.1f}%")

        except Exception as e:
            logger.error(f"Erro ao processar evento HubSoftBulkSyncCompleted: {e}")