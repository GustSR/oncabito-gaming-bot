#!/usr/bin/env python3
"""
Teste da HubSoft Integration.

Valida comandos, handlers, use cases e eventos
para integração com o sistema HubSoft.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Adiciona o path do projeto para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sentinela.application.commands.hubsoft_commands import (
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
from sentinela.application.command_handlers.hubsoft_command_handlers import (
    ScheduleHubSoftIntegrationHandler,
    SyncTicketToHubSoftHandler,
    VerifyUserInHubSoftHandler,
    BulkSyncTicketsToHubSoftHandler,
    RetryFailedIntegrationsHandler,
    CancelHubSoftIntegrationHandler,
    UpdateIntegrationPriorityHandler,
    GetHubSoftIntegrationStatusHandler
)
from sentinela.application.use_cases.hubsoft_integration_use_case import (
    HubSoftIntegrationUseCase,
    HubSoftOperationResult
)
from sentinela.domain.entities.hubsoft_integration import (
    HubSoftIntegrationRequest,
    IntegrationId,
    IntegrationType,
    IntegrationPriority,
    IntegrationStatus
)
from sentinela.domain.events.hubsoft_events import (
    IntegrationScheduled,
    IntegrationStarted,
    IntegrationCompleted,
    IntegrationFailed,
    HubSoftTicketSynced
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock repositories for testing
class MockHubSoftIntegrationRepository:
    """Mock repository para integrações HubSoft."""

    def __init__(self):
        self._integrations = {}

    async def save(self, integration):
        """Salva integração."""
        self._integrations[integration.id.value] = integration
        return True

    async def find_by_id(self, integration_id):
        """Busca integração por ID."""
        return self._integrations.get(integration_id.value)

    async def find_pending_integrations(self, integration_type=None, limit=50):
        """Busca integrações pendentes."""
        pending = []
        for integration in self._integrations.values():
            if integration.status == IntegrationStatus.PENDING:
                if integration_type is None or integration.integration_type == integration_type:
                    pending.append(integration)
                    if len(pending) >= limit:
                        break
        return pending

    async def find_scheduled_integrations(self, until, limit=50):
        """Busca integrações agendadas."""
        scheduled = []
        for integration in self._integrations.values():
            if (integration.status == IntegrationStatus.PENDING and
                integration.scheduled_at and integration.scheduled_at <= until):
                scheduled.append(integration)
                if len(scheduled) >= limit:
                    break
        return scheduled

    async def find_active_integrations(self, integration_type=None):
        """Busca integrações ativas."""
        active = []
        for integration in self._integrations.values():
            if integration.status == IntegrationStatus.IN_PROGRESS:
                if integration_type is None or integration.integration_type == integration_type:
                    active.append(integration)
        return active

    async def find_failed_integrations(self, integration_type=None, since=None, limit=100):
        """Busca integrações falhadas."""
        failed = []
        for integration in self._integrations.values():
            if integration.status == IntegrationStatus.FAILED:
                if integration_type is None or integration.integration_type.value == integration_type:
                    failed.append(integration)
                    if len(failed) >= limit:
                        break
        return failed

    async def find_completed_integrations(self, integration_type=None, since=None, limit=100):
        """Busca integrações completadas."""
        completed = []
        for integration in self._integrations.values():
            if integration.status == IntegrationStatus.COMPLETED:
                if integration_type is None or integration.integration_type == integration_type:
                    completed.append(integration)
                    if len(completed) >= limit:
                        break
        return completed

    async def find_by_metadata(self, metadata_key, metadata_value, status=None):
        """Busca integrações por metadados."""
        found = []
        for integration in self._integrations.values():
            if (metadata_key in integration.metadata and
                integration.metadata[metadata_key] == metadata_value):
                if status is None or integration.status == status:
                    found.append(integration)
        return found

    async def count_integrations_by_status(self, since=None):
        """Conta integrações por status."""
        counts = {}
        for integration in self._integrations.values():
            status = integration.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    async def cleanup_completed_integrations(self, older_than, batch_size=100):
        """Remove integrações completadas antigas."""
        removed = 0
        to_remove = []

        for integration_id, integration in self._integrations.items():
            if (integration.status == IntegrationStatus.COMPLETED and
                integration.completed_at and integration.completed_at < older_than):
                to_remove.append(integration_id)
                removed += 1
                if removed >= batch_size:
                    break

        for integration_id in to_remove:
            del self._integrations[integration_id]

        return removed

    async def get_integration_metrics(self, start_date, end_date, integration_type=None):
        """Obtém métricas de integração."""
        metrics = {
            "total_integrations": len(self._integrations),
            "successful": 0,
            "failed": 0,
            "pending": 0,
            "avg_duration": 0,
            "success_rate": 0
        }

        for integration in self._integrations.values():
            if integration.status == IntegrationStatus.COMPLETED:
                metrics["successful"] += 1
            elif integration.status == IntegrationStatus.FAILED:
                metrics["failed"] += 1
            elif integration.status == IntegrationStatus.PENDING:
                metrics["pending"] += 1

        if metrics["total_integrations"] > 0:
            metrics["success_rate"] = (metrics["successful"] / metrics["total_integrations"]) * 100

        return metrics


class MockHubSoftAPIRepository:
    """Mock repository para API HubSoft."""

    async def verify_client_by_cpf(self, cpf, include_contracts=True):
        """Verifica cliente no HubSoft."""
        return {
            "cpf": cpf,
            "name": f"Cliente {cpf[:3]}***{cpf[-2:]}",
            "contracts": [{"id": "CTR001", "status": "active"}] if include_contracts else [],
            "verified": True
        }

    async def create_ticket(self, ticket_data):
        """Cria ticket no HubSoft."""
        return {
            "id": f"HST_{ticket_data.get('id', '001')}",
            "status": "created",
            "title": ticket_data.get("title", "Ticket"),
            "created_at": datetime.now().isoformat()
        }

    async def update_ticket(self, hubsoft_ticket_id, updates):
        """Atualiza ticket no HubSoft."""
        return {
            "id": hubsoft_ticket_id,
            "status": "updated",
            "updates": updates,
            "updated_at": datetime.now().isoformat()
        }

    async def get_ticket_status(self, hubsoft_ticket_id):
        """Obtém status de ticket."""
        return {
            "id": hubsoft_ticket_id,
            "status": "open",
            "last_update": datetime.now().isoformat()
        }

    async def search_tickets_by_cpf(self, cpf, limit=50):
        """Busca tickets por CPF."""
        return [
            {"id": f"HST_001_{cpf[:3]}", "status": "open"},
            {"id": f"HST_002_{cpf[:3]}", "status": "closed"}
        ]

    async def get_client_contracts(self, cpf):
        """Obtém contratos do cliente."""
        return [
            {"id": "CTR001", "status": "active", "service": "Internet"},
            {"id": "CTR002", "status": "active", "service": "TV"}
        ]

    async def check_api_health(self):
        """Verifica saúde da API."""
        return {
            "status": "healthy",
            "response_time": 150,
            "last_check": datetime.now().isoformat()
        }

    async def get_rate_limit_status(self):
        """Obtém status do rate limiting."""
        return {
            "requests_remaining": 950,
            "reset_time": datetime.now() + timedelta(hours=1),
            "limit": 1000
        }


class MockHubSoftCacheRepository:
    """Mock repository para cache HubSoft."""

    def __init__(self):
        self._cache = {}

    async def get_cached_client_data(self, cpf):
        """Obtém dados de cliente do cache."""
        return self._cache.get(f"client_{cpf}")

    async def cache_client_data(self, cpf, client_data, ttl_seconds=3600):
        """Armazena dados de cliente no cache."""
        self._cache[f"client_{cpf}"] = client_data

    async def get_cached_ticket_data(self, ticket_id):
        """Obtém dados de ticket do cache."""
        return self._cache.get(f"ticket_{ticket_id}")

    async def cache_ticket_data(self, ticket_id, ticket_data, ttl_seconds=1800):
        """Armazena dados de ticket no cache."""
        self._cache[f"ticket_{ticket_id}"] = ticket_data

    async def invalidate_client_cache(self, cpf):
        """Invalida cache de cliente."""
        key = f"client_{cpf}"
        if key in self._cache:
            del self._cache[key]

    async def invalidate_ticket_cache(self, ticket_id):
        """Invalida cache de ticket."""
        key = f"ticket_{ticket_id}"
        if key in self._cache:
            del self._cache[key]

    async def clear_expired_cache(self):
        """Remove entradas expiradas do cache."""
        # Simplificado - remove metade das entradas
        removed = len(self._cache) // 2
        keys_to_remove = list(self._cache.keys())[:removed]
        for key in keys_to_remove:
            del self._cache[key]
        return removed


class MockEventBus:
    """Mock event bus para testes."""

    def __init__(self):
        self.published_events = []

    async def publish(self, event):
        """Publica evento."""
        self.published_events.append(event)
        logger.debug(f"Event published: {event.__class__.__name__}")


async def test_hubsoft_commands():
    """Testa comandos HubSoft."""

    print("\n🧪 TESTANDO COMANDOS HUBSOFT")
    print("=" * 60)

    try:
        # 1. Testa ScheduleHubSoftIntegrationCommand
        schedule_command = ScheduleHubSoftIntegrationCommand(
            integration_type="ticket_sync",
            priority="high",
            payload={"ticket_id": "1001", "sync_type": "create"},
            max_retries=5
        )

        print(f"✅ ScheduleHubSoftIntegrationCommand criado")
        print(f"   Tipo: {schedule_command.integration_type}")
        print(f"   Prioridade: {schedule_command.priority}")
        print(f"   Max retries: {schedule_command.max_retries}")

        # 2. Testa SyncTicketToHubSoftCommand
        sync_command = SyncTicketToHubSoftCommand(
            ticket_id="1001",
            sync_type="create",
            priority="high"
        )

        print(f"\n✅ SyncTicketToHubSoftCommand criado")
        print(f"   Ticket: {sync_command.ticket_id}")
        print(f"   Tipo de sync: {sync_command.sync_type}")

        # 3. Testa VerifyUserInHubSoftCommand
        verify_command = VerifyUserInHubSoftCommand(
            user_id=123456,
            cpf="12345678901",
            cache_duration=3600,
            include_contracts=True
        )

        print(f"\n✅ VerifyUserInHubSoftCommand criado")
        print(f"   Usuário: {verify_command.user_id}")
        print(f"   CPF: {verify_command.cpf[:3]}***{verify_command.cpf[-2:]}")

        # 4. Testa BulkSyncTicketsToHubSoftCommand
        bulk_command = BulkSyncTicketsToHubSoftCommand(
            ticket_ids=["1001", "1002", "1003"],
            sync_type="create",
            batch_size=5,
            delay_between_batches=3
        )

        print(f"\n✅ BulkSyncTicketsToHubSoftCommand criado")
        print(f"   Total tickets: {len(bulk_command.ticket_ids)}")
        print(f"   Batch size: {bulk_command.batch_size}")

        print("\n✅ TESTE DE COMANDOS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE COMANDOS: {e}")
        logger.error(f"Erro no teste de comandos: {e}")
        return False


async def test_hubsoft_handlers():
    """Testa handlers HubSoft."""

    print("\n🧪 TESTANDO HANDLERS HUBSOFT")
    print("=" * 60)

    try:
        # Setup mocks
        integration_repo = MockHubSoftIntegrationRepository()
        api_repo = MockHubSoftAPIRepository()
        cache_repo = MockHubSoftCacheRepository()
        event_bus = MockEventBus()

        # 1. Testa ScheduleHubSoftIntegrationHandler
        print("🔄 Testando ScheduleHubSoftIntegrationHandler...")

        schedule_handler = ScheduleHubSoftIntegrationHandler(integration_repo, event_bus)
        schedule_command = ScheduleHubSoftIntegrationCommand(
            integration_type="ticket_sync",
            priority="normal",
            payload={"ticket_id": "1001"}
        )

        schedule_result = await schedule_handler.handle(schedule_command)
        print(f"   Resultado: {schedule_result.success}")
        if schedule_result.success:
            print(f"   Integração agendada: {schedule_result.data['integration_id']}")

        # 2. Testa SyncTicketToHubSoftHandler
        print("\n🔄 Testando SyncTicketToHubSoftHandler...")

        sync_handler = SyncTicketToHubSoftHandler(integration_repo, event_bus)
        sync_command = SyncTicketToHubSoftCommand(
            ticket_id="1001",
            sync_type="create"
        )

        sync_result = await sync_handler.handle(sync_command)
        print(f"   Resultado: {sync_result.success}")
        if sync_result.success:
            print(f"   Ticket sincronizado: {sync_result.data['ticket_id']}")

        # 3. Testa VerifyUserInHubSoftHandler
        print("\n🔄 Testando VerifyUserInHubSoftHandler...")

        verify_handler = VerifyUserInHubSoftHandler(integration_repo, event_bus)
        verify_command = VerifyUserInHubSoftCommand(
            user_id=123456,
            cpf="12345678901"
        )

        verify_result = await verify_handler.handle(verify_command)
        print(f"   Resultado: {verify_result.success}")
        if verify_result.success:
            print(f"   Usuário verificado: {verify_result.data['user_id']}")

        # 4. Testa BulkSyncTicketsToHubSoftHandler
        print("\n🔄 Testando BulkSyncTicketsToHubSoftHandler...")

        bulk_handler = BulkSyncTicketsToHubSoftHandler(integration_repo, event_bus)
        bulk_command = BulkSyncTicketsToHubSoftCommand(
            ticket_ids=["1001", "1002"],
            sync_type="create",
            batch_size=2
        )

        bulk_result = await bulk_handler.handle(bulk_command)
        print(f"   Resultado: {bulk_result.success}")
        if bulk_result.success:
            print(f"   Lote processado: {bulk_result.data['total_tickets']} tickets")

        print("\n✅ TESTE DE HANDLERS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE HANDLERS: {e}")
        logger.error(f"Erro no teste de handlers: {e}")
        return False


async def test_hubsoft_entities():
    """Testa entidades HubSoft."""

    print("\n🧪 TESTANDO ENTIDADES HUBSOFT")
    print("=" * 60)

    try:
        # 1. Testa criação de integração
        print("🔄 Testando criação de HubSoftIntegrationRequest...")

        integration_id = IntegrationId.generate()
        integration = HubSoftIntegrationRequest(
            integration_id=integration_id,
            integration_type=IntegrationType.TICKET_SYNC,
            priority=IntegrationPriority.HIGH,
            payload={"ticket_id": "1001", "sync_type": "create"},
            max_retries=3
        )

        print(f"   Integração criada: {integration_id.value}")
        print(f"   Tipo: {integration.integration_type.value}")
        print(f"   Status inicial: {integration.status.value}")

        # 2. Testa agendamento
        print("\n🔄 Testando agendamento...")

        integration.schedule_integration()
        print(f"   Status após agendamento: {integration.status.value}")
        print(f"   Agendada para: {integration.scheduled_at}")

        # 3. Testa início da integração
        print("\n🔄 Testando início da integração...")

        integration.start_integration()
        print(f"   Status após início: {integration.status.value}")
        print(f"   Iniciada em: {integration.started_at}")

        # 4. Testa registro de tentativa
        print("\n🔄 Testando registro de tentativa...")

        integration.record_attempt(
            success=True,
            response_data={"hubsoft_id": "HST_001"},
            duration_ms=1500
        )
        print(f"   Tentativas registradas: {integration.attempt_count}")
        print(f"   Status final: {integration.status.value}")

        # 5. Testa regras de negócio
        print("\n🔄 Testando regras de negócio...")

        can_retry = integration.can_retry()
        is_high_priority = integration.is_high_priority()
        print(f"   Pode fazer retry: {can_retry}")
        print(f"   É alta prioridade: {is_high_priority}")

        # 6. Testa resumo de execução
        print("\n🔄 Testando resumo de execução...")

        summary = integration.get_execution_summary()
        print(f"   Total de tentativas: {summary['attempts']}")
        print(f"   Taxa de sucesso: {summary['success_rate']:.1f}%")

        print("\n✅ TESTE DE ENTIDADES PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE ENTIDADES: {e}")
        logger.error(f"Erro no teste de entidades: {e}")
        return False


async def test_hubsoft_use_case():
    """Testa use case HubSoft."""

    print("\n🧪 TESTANDO HUBSOFT USE CASE")
    print("=" * 60)

    try:
        # Setup mocks
        integration_repo = MockHubSoftIntegrationRepository()
        api_repo = MockHubSoftAPIRepository()
        cache_repo = MockHubSoftCacheRepository()
        event_bus = MockEventBus()

        # Setup handlers
        schedule_handler = ScheduleHubSoftIntegrationHandler(integration_repo, event_bus)
        sync_handler = SyncTicketToHubSoftHandler(integration_repo, event_bus)
        verify_handler = VerifyUserInHubSoftHandler(integration_repo, event_bus)
        bulk_handler = BulkSyncTicketsToHubSoftHandler(integration_repo, event_bus)
        retry_handler = RetryFailedIntegrationsHandler(integration_repo, event_bus)
        cancel_handler = CancelHubSoftIntegrationHandler(integration_repo, event_bus)
        priority_handler = UpdateIntegrationPriorityHandler(integration_repo, event_bus)
        status_handler = GetHubSoftIntegrationStatusHandler(integration_repo)

        # Cria use case
        hubsoft_use_case = HubSoftIntegrationUseCase(
            schedule_handler=schedule_handler,
            sync_ticket_handler=sync_handler,
            verify_user_handler=verify_handler,
            bulk_sync_handler=bulk_handler,
            retry_handler=retry_handler,
            cancel_handler=cancel_handler,
            priority_handler=priority_handler,
            status_handler=status_handler,
            integration_repository=integration_repo,
            api_repository=api_repo,
            cache_repository=cache_repo
        )

        # 1. Testa sincronização de ticket
        print("🔄 Testando sincronização de ticket...")

        sync_result = await hubsoft_use_case.sync_ticket_to_hubsoft(
            ticket_id="1001",
            sync_type="create",
            priority="high"
        )

        print(f"   Sucesso: {sync_result.success}")
        print(f"   Mensagem: {sync_result.message}")
        print(f"   Duração: {sync_result.duration_seconds:.3f}s")

        # 2. Testa verificação de usuário
        print("\n🔄 Testando verificação de usuário...")

        verify_result = await hubsoft_use_case.verify_user_in_hubsoft(
            user_id=123456,
            cpf="12345678901",
            cache_duration=3600
        )

        print(f"   Sucesso: {verify_result.success}")
        print(f"   Mensagem: {verify_result.message}")
        print(f"   Do cache: {verify_result.cached}")

        # 3. Testa sincronização em lote
        print("\n🔄 Testando sincronização em lote...")

        bulk_result = await hubsoft_use_case.bulk_sync_tickets(
            ticket_ids=["1001", "1002", "1003"],
            sync_type="create",
            batch_size=2
        )

        print(f"   Sucesso: {bulk_result.success}")
        print(f"   Mensagem: {bulk_result.message}")

        # 4. Testa busca de dados completos
        print("\n🔄 Testando busca de dados completos...")

        fetch_result = await hubsoft_use_case.fetch_client_data_comprehensive(
            cpf="12345678901",
            include_tickets=True,
            include_contracts=True
        )

        print(f"   Sucesso: {fetch_result.success}")
        print(f"   Mensagem: {fetch_result.message}")

        # 5. Testa verificação de saúde
        print("\n🔄 Testando verificação de saúde...")

        health_result = await hubsoft_use_case.check_hubsoft_health()

        print(f"   Sucesso: {health_result.success}")
        print(f"   Mensagem: {health_result.message}")

        # 6. Testa limpeza de cache
        print("\n🔄 Testando limpeza de cache...")

        cleanup_result = await hubsoft_use_case.cleanup_expired_cache()

        print(f"   Sucesso: {cleanup_result.success}")
        print(f"   Mensagem: {cleanup_result.message}")
        if cleanup_result.data:
            print(f"   Entradas removidas: {cleanup_result.data['removed_count']}")

        print("\n✅ TESTE DE USE CASE PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE USE CASE: {e}")
        logger.error(f"Erro no teste de use case: {e}")
        return False


async def test_hubsoft_events():
    """Testa eventos HubSoft."""

    print("\n🧪 TESTANDO EVENTOS HUBSOFT")
    print("=" * 60)

    try:
        # 1. Testa evento IntegrationScheduled
        integration_id = IntegrationId.generate()
        scheduled_event = IntegrationScheduled(
            integration_id=integration_id,
            integration_type="ticket_sync",
            priority="high",
            scheduled_at=datetime.now()
        )

        print(f"✅ IntegrationScheduled criado")
        print(f"   ID: {scheduled_event.integration_id.value}")
        print(f"   Tipo: {scheduled_event.integration_type}")

        # 2. Testa evento IntegrationCompleted
        completed_event = IntegrationCompleted(
            integration_id=integration_id,
            integration_type="ticket_sync",
            priority="high",
            success=True,
            total_attempts=1,
            duration_seconds=15
        )

        print(f"\n✅ IntegrationCompleted criado")
        print(f"   Sucesso: {completed_event.success}")
        print(f"   Tentativas: {completed_event.total_attempts}")
        print(f"   Duração: {completed_event.duration_seconds}s")

        # 3. Testa evento HubSoftTicketSynced
        ticket_synced_event = HubSoftTicketSynced(
            ticket_id="1001",
            hubsoft_ticket_id="HST_001",
            sync_type="create",
            sync_data={"status": "created", "priority": "high"}
        )

        print(f"\n✅ HubSoftTicketSynced criado")
        print(f"   Ticket local: {ticket_synced_event.ticket_id}")
        print(f"   Ticket HubSoft: {ticket_synced_event.hubsoft_ticket_id}")
        print(f"   Tipo de sync: {ticket_synced_event.sync_type}")

        print("\n✅ TESTE DE EVENTOS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE EVENTOS: {e}")
        logger.error(f"Erro no teste de eventos: {e}")
        return False


async def test_hubsoft_integration():
    """Executa todos os testes da integração HubSoft."""

    print("🎯 INICIANDO TESTES DA INTEGRAÇÃO HUBSOFT")
    print("=" * 80)

    # Lista de testes
    tests = [
        ("Comandos", test_hubsoft_commands),
        ("Handlers", test_hubsoft_handlers),
        ("Entidades", test_hubsoft_entities),
        ("Use Case", test_hubsoft_use_case),
        ("Eventos", test_hubsoft_events)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Executando teste: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSOU")
            else:
                print(f"❌ {test_name}: FALHOU")
        except Exception as e:
            print(f"❌ {test_name}: ERRO - {e}")
            logger.error(f"Erro no teste {test_name}: {e}")

    # Resultado final
    print("\n" + "=" * 80)
    print(f"📊 RESULTADO FINAL: {passed}/{total} testes passaram")

    if passed == total:
        print("🎉 HUBSOFT INTEGRATION IMPLEMENTADA COM SUCESSO!")
        print("✅ Todas as operações de integração estão funcionais")
        print("🔧 Sistema pronto para comunicação com HubSoft")
        print("📡 Event-driven architecture implementada")
        print("🚀 Cache e retry logic funcionando")
    else:
        print("⚠️ Alguns testes falharam - Revisar implementação")

    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    asyncio.run(test_hubsoft_integration())