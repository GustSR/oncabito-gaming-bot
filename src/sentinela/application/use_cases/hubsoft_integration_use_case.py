"""
HubSoft Integration Use Case.

Orquestra operações de integração com HubSoft, fornecendo
interface de alto nível para sincronização de dados e comunicação
com o sistema externo.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..commands.hubsoft_commands import (
    ScheduleHubSoftIntegrationCommand,
    SyncTicketToHubSoftCommand,
    VerifyUserInHubSoftCommand,
    FetchClientDataFromHubSoftCommand,
    BulkSyncTicketsToHubSoftCommand,
    RetryFailedIntegrationsCommand,
    CancelHubSoftIntegrationCommand,
    UpdateIntegrationPriorityCommand,
    GetHubSoftIntegrationStatusCommand
)
from ..command_handlers.hubsoft_command_handlers import (
    ScheduleHubSoftIntegrationHandler,
    SyncTicketToHubSoftHandler,
    VerifyUserInHubSoftHandler,
    BulkSyncTicketsToHubSoftHandler,
    RetryFailedIntegrationsHandler,
    CancelHubSoftIntegrationHandler,
    UpdateIntegrationPriorityHandler,
    GetHubSoftIntegrationStatusHandler
)
from ...domain.repositories.hubsoft_repository import (
    HubSoftIntegrationRepository,
    HubSoftAPIRepository,
    HubSoftCacheRepository
)
from ...domain.entities.hubsoft_integration import IntegrationType, IntegrationPriority

logger = logging.getLogger(__name__)


@dataclass
class HubSoftOperationResult:
    """
    Resultado de uma operação HubSoft.

    Attributes:
        success: Se a operação foi bem-sucedida
        message: Mensagem descritiva
        integration_id: ID da integração (se aplicável)
        data: Dados retornados pela operação
        error_code: Código de erro (se aplicável)
        duration_seconds: Duração da operação
        cached: Se o resultado veio do cache
    """
    success: bool
    message: str
    integration_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    duration_seconds: Optional[float] = None
    cached: bool = False


class HubSoftIntegrationUseCase:
    """
    Use case para operações de integração com HubSoft.

    Fornece interface unificada para todas as operações de integração,
    incluindo sincronização de tickets, verificação de usuários e
    gerenciamento de cache.
    """

    def __init__(
        self,
        schedule_handler: ScheduleHubSoftIntegrationHandler,
        sync_ticket_handler: SyncTicketToHubSoftHandler,
        verify_user_handler: VerifyUserInHubSoftHandler,
        bulk_sync_handler: BulkSyncTicketsToHubSoftHandler,
        retry_handler: RetryFailedIntegrationsHandler,
        cancel_handler: CancelHubSoftIntegrationHandler,
        priority_handler: UpdateIntegrationPriorityHandler,
        status_handler: GetHubSoftIntegrationStatusHandler,
        integration_repository: HubSoftIntegrationRepository,
        api_repository: HubSoftAPIRepository,
        cache_repository: HubSoftCacheRepository
    ):
        self.schedule_handler = schedule_handler
        self.sync_ticket_handler = sync_ticket_handler
        self.verify_user_handler = verify_user_handler
        self.bulk_sync_handler = bulk_sync_handler
        self.retry_handler = retry_handler
        self.cancel_handler = cancel_handler
        self.priority_handler = priority_handler
        self.status_handler = status_handler
        self.integration_repository = integration_repository
        self.api_repository = api_repository
        self.cache_repository = cache_repository

    # Operações de Sincronização de Tickets

    async def sync_ticket_to_hubsoft(
        self,
        ticket_id: str,
        sync_type: str,
        hubsoft_ticket_id: Optional[str] = None,
        priority: str = "normal",
        force_sync: bool = False
    ) -> HubSoftOperationResult:
        """
        Sincroniza ticket com HubSoft.

        Args:
            ticket_id: ID do ticket local
            sync_type: Tipo de sincronização (create, update, status_change)
            hubsoft_ticket_id: ID do ticket no HubSoft (para updates)
            priority: Prioridade da sincronização
            force_sync: Forçar sincronização mesmo se já sincronizado

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            # Valida parâmetros
            if sync_type not in ["create", "update", "status_change"]:
                return HubSoftOperationResult(
                    success=False,
                    message=f"Tipo de sincronização inválido: {sync_type}",
                    error_code="INVALID_SYNC_TYPE"
                )

            if sync_type in ["update", "status_change"] and not hubsoft_ticket_id:
                return HubSoftOperationResult(
                    success=False,
                    message="hubsoft_ticket_id é obrigatório para updates",
                    error_code="MISSING_HUBSOFT_ID"
                )

            # Executa sincronização
            command = SyncTicketToHubSoftCommand(
                ticket_id=ticket_id,
                sync_type=sync_type,
                hubsoft_ticket_id=hubsoft_ticket_id,
                priority=priority,
                force_sync=force_sync
            )

            result = await self.sync_ticket_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                integration_id=result.data.get("integration_id") if result.data else None,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro na sincronização de ticket: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na sincronização: {str(e)}",
                error_code="SYNC_ERROR"
            )

    async def bulk_sync_tickets(
        self,
        ticket_ids: List[str],
        sync_type: str,
        batch_size: int = 10,
        priority: str = "normal",
        delay_between_batches: int = 5
    ) -> HubSoftOperationResult:
        """
        Sincroniza múltiplos tickets em lote.

        Args:
            ticket_ids: Lista de IDs de tickets
            sync_type: Tipo de sincronização
            batch_size: Tamanho do lote
            priority: Prioridade da operação
            delay_between_batches: Delay entre lotes em segundos

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            if not ticket_ids:
                return HubSoftOperationResult(
                    success=False,
                    message="Lista de tickets não pode estar vazia",
                    error_code="EMPTY_TICKET_LIST"
                )

            command = BulkSyncTicketsToHubSoftCommand(
                ticket_ids=ticket_ids,
                sync_type=sync_type,
                batch_size=batch_size,
                priority=priority,
                delay_between_batches=delay_between_batches
            )

            result = await self.bulk_sync_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                integration_id=result.data.get("integration_id") if result.data else None,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro na sincronização em lote: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na sincronização em lote: {str(e)}",
                error_code="BULK_SYNC_ERROR"
            )

    # Operações de Verificação de Usuários

    async def verify_user_in_hubsoft(
        self,
        user_id: int,
        cpf: str,
        cache_duration: int = 3600,
        force_refresh: bool = False,
        include_contracts: bool = True
    ) -> HubSoftOperationResult:
        """
        Verifica usuário no HubSoft.

        Args:
            user_id: ID do usuário local
            cpf: CPF para verificação
            cache_duration: Duração do cache em segundos
            force_refresh: Forçar atualização do cache
            include_contracts: Incluir dados de contratos

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            # Valida CPF
            if not self._validate_cpf(cpf):
                return HubSoftOperationResult(
                    success=False,
                    message="CPF inválido",
                    error_code="INVALID_CPF"
                )

            # Verifica cache primeiro se não forçar refresh
            cached_data = None
            if not force_refresh:
                cached_data = await self.cache_repository.get_cached_client_data(cpf)

            if cached_data:
                duration = (datetime.now() - start_time).total_seconds()
                return HubSoftOperationResult(
                    success=True,
                    message="Dados obtidos do cache",
                    data=cached_data,
                    duration_seconds=duration,
                    cached=True
                )

            # Executa verificação
            command = VerifyUserInHubSoftCommand(
                user_id=user_id,
                cpf=cpf,
                cache_duration=cache_duration,
                force_refresh=force_refresh,
                include_contracts=include_contracts
            )

            result = await self.verify_user_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                integration_id=result.data.get("integration_id") if result.data else None,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro na verificação de usuário: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na verificação: {str(e)}",
                error_code="VERIFICATION_ERROR"
            )

    async def fetch_client_data_comprehensive(
        self,
        cpf: str,
        include_tickets: bool = True,
        include_contracts: bool = True,
        include_billing: bool = False,
        cache_duration: int = 3600
    ) -> HubSoftOperationResult:
        """
        Busca dados completos de cliente no HubSoft.

        Args:
            cpf: CPF do cliente
            include_tickets: Incluir tickets existentes
            include_contracts: Incluir dados de contratos
            include_billing: Incluir dados de faturamento
            cache_duration: Duração do cache em segundos

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            # Valida CPF
            if not self._validate_cpf(cpf):
                return HubSoftOperationResult(
                    success=False,
                    message="CPF inválido",
                    error_code="INVALID_CPF"
                )

            # Agenda integração
            command = ScheduleHubSoftIntegrationCommand(
                integration_type=IntegrationType.CLIENT_DATA_FETCH.value,
                priority=IntegrationPriority.HIGH.value,
                payload={
                    "cpf": cpf,
                    "include_tickets": include_tickets,
                    "include_contracts": include_contracts,
                    "include_billing": include_billing,
                    "cache_duration": cache_duration
                }
            )

            result = await self.schedule_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                integration_id=result.data.get("integration_id") if result.data else None,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro na busca de dados: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na busca de dados: {str(e)}",
                error_code="FETCH_ERROR"
            )

    # Operações de Gerenciamento

    async def retry_failed_integrations(
        self,
        integration_type: Optional[str] = None,
        max_age_hours: int = 24,
        limit: int = 50,
        force_retry: bool = False
    ) -> HubSoftOperationResult:
        """
        Retenta integrações falhadas.

        Args:
            integration_type: Tipo de integração (None = todas)
            max_age_hours: Idade máxima das integrações em horas
            limit: Limite de integrações para retentar
            force_retry: Forçar retry mesmo se excedeu tentativas

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            command = RetryFailedIntegrationsCommand(
                integration_type=integration_type,
                max_age_hours=max_age_hours,
                limit=limit,
                force_retry=force_retry
            )

            result = await self.retry_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro ao retentar integrações: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro ao retentar integrações: {str(e)}",
                error_code="RETRY_ERROR"
            )

    async def cancel_integration(
        self,
        integration_id: str,
        reason: str = "Cancelado pelo usuário"
    ) -> HubSoftOperationResult:
        """
        Cancela integração pendente.

        Args:
            integration_id: ID da integração
            reason: Motivo do cancelamento

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            command = CancelHubSoftIntegrationCommand(
                integration_id=integration_id,
                reason=reason
            )

            result = await self.cancel_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro ao cancelar integração: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro ao cancelar integração: {str(e)}",
                error_code="CANCEL_ERROR"
            )

    async def get_integration_status(
        self,
        integration_id: Optional[str] = None,
        include_attempts: bool = False,
        include_payload: bool = False
    ) -> HubSoftOperationResult:
        """
        Obtém status de integrações.

        Args:
            integration_id: ID da integração (None = todas ativas)
            include_attempts: Incluir histórico de tentativas
            include_payload: Incluir dados da integração

        Returns:
            Resultado da operação
        """
        try:
            start_time = datetime.now()

            command = GetHubSoftIntegrationStatusCommand(
                integration_id=integration_id,
                include_attempts=include_attempts,
                include_payload=include_payload
            )

            result = await self.status_handler.handle(command)
            duration = (datetime.now() - start_time).total_seconds()

            return HubSoftOperationResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro ao obter status: {str(e)}",
                error_code="STATUS_ERROR"
            )

    # Operações de Cache

    async def invalidate_client_cache(
        self,
        cpf: str
    ) -> HubSoftOperationResult:
        """
        Invalida cache de cliente.

        Args:
            cpf: CPF do cliente

        Returns:
            Resultado da operação
        """
        try:
            await self.cache_repository.invalidate_client_cache(cpf)

            return HubSoftOperationResult(
                success=True,
                message="Cache de cliente invalidado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro ao invalidar cache: {str(e)}",
                error_code="CACHE_ERROR"
            )

    async def cleanup_expired_cache(self) -> HubSoftOperationResult:
        """
        Remove entradas expiradas do cache.

        Returns:
            Resultado da operação
        """
        try:
            count = await self.cache_repository.clear_expired_cache()

            return HubSoftOperationResult(
                success=True,
                message=f"Limpeza concluída: {count} entradas removidas",
                data={"removed_count": count}
            )

        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na limpeza do cache: {str(e)}",
                error_code="CLEANUP_ERROR"
            )

    # Operações de Monitoramento

    async def get_integration_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        integration_type: Optional[str] = None
    ) -> HubSoftOperationResult:
        """
        Obtém métricas de integração.

        Args:
            start_date: Data de início
            end_date: Data de fim
            integration_type: Tipo de integração (None = todos)

        Returns:
            Resultado da operação
        """
        try:
            # Converte string para enum se necessário
            integration_type_enum = None
            if integration_type:
                integration_type_enum = IntegrationType(integration_type)

            metrics = await self.integration_repository.get_integration_metrics(
                start_date=start_date,
                end_date=end_date,
                integration_type=integration_type_enum
            )

            return HubSoftOperationResult(
                success=True,
                message="Métricas obtidas com sucesso",
                data=metrics
            )

        except Exception as e:
            logger.error(f"Erro ao obter métricas: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro ao obter métricas: {str(e)}",
                error_code="METRICS_ERROR"
            )

    async def check_hubsoft_health(self) -> HubSoftOperationResult:
        """
        Verifica saúde da API HubSoft.

        Returns:
            Resultado da operação
        """
        try:
            health_data = await self.api_repository.check_api_health()

            return HubSoftOperationResult(
                success=True,
                message="Verificação de saúde concluída",
                data=health_data
            )

        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return HubSoftOperationResult(
                success=False,
                message=f"Erro na verificação de saúde: {str(e)}",
                error_code="HEALTH_CHECK_ERROR"
            )

    # Métodos auxiliares

    def _validate_cpf(self, cpf: str) -> bool:
        """
        Valida formato básico do CPF.

        Args:
            cpf: CPF a ser validado

        Returns:
            True se válido, False caso contrário
        """
        # Remove formatação
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        # Verifica se tem 11 dígitos
        if len(cpf_clean) != 11:
            return False

        # Verifica se não são todos iguais
        if cpf_clean == cpf_clean[0] * 11:
            return False

        # Validação simplificada - em produção usaria algoritmo completo
        return True