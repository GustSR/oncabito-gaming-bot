"""
Dependency Injection Container.

Configura e gerencia todas as dependências do sistema,
incluindo repositories, services e handlers.
"""

import logging
from typing import Dict, Any, Optional
import os
from pathlib import Path

# Domain
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.repositories.hubsoft_repository import (
    HubSoftIntegrationRepository,
    HubSoftAPIRepository,
    HubSoftCacheRepository
)

# Infrastructure
from ..repositories.sqlite_ticket_repository import SQLiteTicketRepository
from ..repositories.sqlite_cpf_verification_repository import SQLiteCPFVerificationRepository
from ..repositories.sqlite_hubsoft_integration_repository import SQLiteHubSoftIntegrationRepository
from ..repositories.sqlite_user_repository import SQLiteUserRepository
try:
    from ..external_services.hubsoft_api_service import HubSoftAPIService, HubSoftCacheService
except ImportError:
    # Fallback para mock services se dependências não estiverem disponíveis
    from ..external_services.mock_hubsoft_api_service import MockHubSoftAPIService as HubSoftAPIService, MockHubSoftCacheService as HubSoftCacheService
from ..events.event_bus import InMemoryEventBus, EventBus

# Application
from ...application.command_handlers.hubsoft_command_handlers import (
    ScheduleHubSoftIntegrationHandler,
    SyncTicketToHubSoftHandler,
    VerifyUserInHubSoftHandler,
    BulkSyncTicketsToHubSoftHandler,
    RetryFailedIntegrationsHandler,
    CancelHubSoftIntegrationHandler,
    UpdateIntegrationPriorityHandler,
    GetHubSoftIntegrationStatusHandler
)
from ...application.command_handlers.cpf_verification_handlers import (
    StartCPFVerificationHandler,
    SubmitCPFForVerificationHandler,
    CancelCPFVerificationHandler
)
from ...application.command_handlers.process_expired_verifications_handler import (
    ProcessExpiredVerificationsHandler
)
from ...application.command_handlers.admin_command_handlers import (
    ListTicketsHandler,
    AssignTicketHandler,
    UpdateTicketStatusHandler,
    BanUserHandler,
    GetSystemStatsHandler
)
from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
from ...application.use_cases.admin_operations_use_case import AdminOperationsUseCase

# Mock external components (for testing)
try:
    from ...integrations.hubsoft.rate_limiter import RateLimiter
    from ...integrations.hubsoft.token_manager import TokenManager
    from ...integrations.hubsoft.cache_manager import CacheManager
except ImportError:
    # Fallback para classes mock
    class RateLimiter:
        def __init__(self, requests_per_minute=60, max_burst=10):
            pass
        async def acquire(self):
            pass
        async def handle_rate_limit(self, retry_after):
            pass
        async def get_status(self):
            return {"status": "mock"}

    class TokenManager:
        def __init__(self):
            self._token = None
        async def get_valid_token(self):
            return "mock_token"
        async def store_token(self, token, expires_in):
            self._token = token

    class CacheManager:
        def __init__(self, max_size=1000, default_ttl=3600, cleanup_interval=300):
            self._cache = {}
        async def get(self, key):
            return self._cache.get(key)
        async def set(self, key, value, ttl):
            self._cache[key] = value
        async def delete(self, key):
            self._cache.pop(key, None)
        async def cleanup_expired(self):
            return 0
        async def shutdown(self):
            pass

logger = logging.getLogger(__name__)


class DIContainer:
    """Container de Dependency Injection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._instances: Dict[str, Any] = {}
        self._config = config or self._load_default_config()
        self._initialized = False

    def _load_default_config(self) -> Dict[str, Any]:
        """Carrega configuração padrão."""
        return {
            # Database
            "database": {
                "path": os.getenv("DB_PATH", "data/oncabo.db")
            },

            # HubSoft API
            "hubsoft": {
                "base_url": os.getenv("HUBSOFT_API_URL", "https://api.hubsoft.com"),
                "username": os.getenv("HUBSOFT_USERNAME", ""),
                "password": os.getenv("HUBSOFT_PASSWORD", ""),
                "timeout_seconds": int(os.getenv("HUBSOFT_TIMEOUT", "30")),
                "rate_limit_per_minute": int(os.getenv("HUBSOFT_RATE_LIMIT", "60")),
                "max_burst": int(os.getenv("HUBSOFT_MAX_BURST", "10"))
            },

            # Cache
            "cache": {
                "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
                "max_size": int(os.getenv("CACHE_MAX_SIZE", "1000")),
                "cleanup_interval": int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))
            },

            # Event Bus
            "events": {
                "max_concurrent_handlers": int(os.getenv("EVENT_MAX_CONCURRENT", "10")),
                "handler_timeout": int(os.getenv("EVENT_HANDLER_TIMEOUT", "30"))
            }
        }

    async def initialize(self) -> None:
        """Inicializa o container."""
        if self._initialized:
            return

        logger.info("Inicializando Dependency Injection Container...")

        try:
            # Registra repositories
            logger.debug("Registrando repositories...")
            await self._register_repositories()

            # Registra external services
            logger.debug("Registrando external services...")
            await self._register_external_services()

            # Registra infrastructure services
            logger.debug("Registrando infrastructure services...")
            await self._register_infrastructure_services()

            # Registra command handlers
            logger.debug("Registrando command handlers...")
            await self._register_command_handlers()

            # Registra use cases
            logger.debug("Registrando use cases...")
            await self._register_use_cases()

            self._initialized = True
            logger.info("Dependency Injection Container inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar container: {e}")
            raise

    async def _register_repositories(self) -> None:
        """Registra repositories."""
        db_path = self._config["database"]["path"]

        # Ticket Repository
        ticket_repo = SQLiteTicketRepository(db_path)
        self._instances["ticket_repository"] = ticket_repo

        # CPF Verification Repository
        cpf_repo = SQLiteCPFVerificationRepository(db_path)
        self._instances["cpf_verification_repository"] = cpf_repo

        # HubSoft Integration Repository
        hubsoft_integration_repo = SQLiteHubSoftIntegrationRepository(db_path)
        self._instances["hubsoft_integration_repository"] = hubsoft_integration_repo

        # User Repository
        user_repo = SQLiteUserRepository(db_path)
        self._instances["user_repository"] = user_repo

        logger.debug("Repositories registrados")

    async def _register_external_services(self) -> None:
        """Registra external services."""
        hubsoft_config = self._config["hubsoft"]
        cache_config = self._config["cache"]

        # Rate Limiter
        rate_limiter = RateLimiter(
            requests_per_minute=hubsoft_config["rate_limit_per_minute"],
            max_burst=hubsoft_config["max_burst"]
        )
        self._instances["rate_limiter"] = rate_limiter

        # Token Manager
        token_manager = TokenManager()
        self._instances["token_manager"] = token_manager

        # Cache Manager
        cache_manager = CacheManager(
            max_size=cache_config["max_size"],
            default_ttl=cache_config["default_ttl"],
            cleanup_interval=cache_config["cleanup_interval"]
        )
        self._instances["cache_manager"] = cache_manager

        # HubSoft API Service
        hubsoft_api = HubSoftAPIService(
            base_url=hubsoft_config["base_url"],
            username=hubsoft_config["username"],
            password=hubsoft_config["password"],
            rate_limiter=rate_limiter,
            token_manager=token_manager,
            timeout_seconds=hubsoft_config["timeout_seconds"]
        )
        self._instances["hubsoft_api_repository"] = hubsoft_api

        # HubSoft Cache Service
        hubsoft_cache = HubSoftCacheService(cache_manager)
        self._instances["hubsoft_cache_repository"] = hubsoft_cache

        logger.debug("External services registrados")

    async def _register_infrastructure_services(self) -> None:
        """Registra infrastructure services."""
        events_config = self._config["events"]

        # Event Bus
        event_bus = InMemoryEventBus(
            max_concurrent_handlers=events_config["max_concurrent_handlers"],
            handler_timeout=events_config["handler_timeout"]
        )
        self._instances["event_bus"] = event_bus

        # Domain Services
        from ...domain.services.cpf_validation_service import CPFValidationService
        from ...domain.services.duplicate_cpf_service import DuplicateCPFService

        cpf_validation_service = CPFValidationService()
        self._instances["cpf_validation_service"] = cpf_validation_service

        duplicate_cpf_service = DuplicateCPFService(
            self._instances["cpf_verification_repository"]
        )
        self._instances["duplicate_cpf_service"] = duplicate_cpf_service

        logger.debug("Infrastructure services registrados")

    async def _register_command_handlers(self) -> None:
        """Registra command handlers."""
        # HubSoft Handlers
        schedule_handler = ScheduleHubSoftIntegrationHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["schedule_hubsoft_integration_handler"] = schedule_handler

        sync_ticket_handler = SyncTicketToHubSoftHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["sync_ticket_to_hubsoft_handler"] = sync_ticket_handler

        verify_user_handler = VerifyUserInHubSoftHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["verify_user_in_hubsoft_handler"] = verify_user_handler

        bulk_sync_handler = BulkSyncTicketsToHubSoftHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["bulk_sync_tickets_handler"] = bulk_sync_handler

        retry_handler = RetryFailedIntegrationsHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["retry_failed_integrations_handler"] = retry_handler

        cancel_handler = CancelHubSoftIntegrationHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["cancel_hubsoft_integration_handler"] = cancel_handler

        priority_handler = UpdateIntegrationPriorityHandler(
            self._instances["hubsoft_integration_repository"],
            self._instances["event_bus"]
        )
        self._instances["update_integration_priority_handler"] = priority_handler

        status_handler = GetHubSoftIntegrationStatusHandler(
            self._instances["hubsoft_integration_repository"]
        )
        self._instances["get_hubsoft_integration_status_handler"] = status_handler

        # CPF Verification Handlers
        start_cpf_handler = StartCPFVerificationHandler(
            self._instances["cpf_verification_repository"],
            self._instances["user_repository"],
            self._instances["event_bus"]
        )
        self._instances["start_cpf_verification_handler"] = start_cpf_handler

        submit_cpf_handler = SubmitCPFForVerificationHandler(
            self._instances["cpf_verification_repository"],
            self._instances["user_repository"],
            self._instances["cpf_validation_service"],
            self._instances["duplicate_cpf_service"],
            self._instances["event_bus"]
        )
        self._instances["submit_cpf_verification_handler"] = submit_cpf_handler

        cancel_cpf_handler = CancelCPFVerificationHandler(
            self._instances["cpf_verification_repository"],
            self._instances["event_bus"]
        )
        self._instances["cancel_cpf_verification_handler"] = cancel_cpf_handler

        process_expired_handler = ProcessExpiredVerificationsHandler(
            self._instances["cpf_verification_repository"],
            self._instances["event_bus"]
        )
        self._instances["process_expired_verifications_handler"] = process_expired_handler

        # Admin Handlers
        list_tickets_handler = ListTicketsHandler(
            self._instances["ticket_repository"]
        )
        self._instances["list_tickets_handler"] = list_tickets_handler

        assign_ticket_handler = AssignTicketHandler(
            self._instances["ticket_repository"],
            self._instances["event_bus"]
        )
        self._instances["assign_ticket_handler"] = assign_ticket_handler

        update_ticket_status_handler = UpdateTicketStatusHandler(
            self._instances["ticket_repository"],
            self._instances["event_bus"]
        )
        self._instances["update_ticket_status_handler"] = update_ticket_status_handler

        ban_user_handler = BanUserHandler(
            self._instances["user_repository"],
            self._instances["event_bus"]
        )
        self._instances["ban_user_handler"] = ban_user_handler

        stats_handler = GetSystemStatsHandler(
            self._instances["ticket_repository"],
            self._instances["user_repository"],
            self._instances["cpf_verification_repository"]
        )
        self._instances["get_system_stats_handler"] = stats_handler

        logger.debug("Command handlers registrados")

    async def _register_use_cases(self) -> None:
        """Registra use cases."""
        # HubSoft Integration Use Case
        hubsoft_use_case = HubSoftIntegrationUseCase(
            schedule_handler=self._instances["schedule_hubsoft_integration_handler"],
            sync_ticket_handler=self._instances["sync_ticket_to_hubsoft_handler"],
            verify_user_handler=self._instances["verify_user_in_hubsoft_handler"],
            bulk_sync_handler=self._instances["bulk_sync_tickets_handler"],
            retry_handler=self._instances["retry_failed_integrations_handler"],
            cancel_handler=self._instances["cancel_hubsoft_integration_handler"],
            priority_handler=self._instances["update_integration_priority_handler"],
            status_handler=self._instances["get_hubsoft_integration_status_handler"],
            integration_repository=self._instances["hubsoft_integration_repository"],
            api_repository=self._instances["hubsoft_api_repository"],
            cache_repository=self._instances["hubsoft_cache_repository"]
        )
        self._instances["hubsoft_integration_use_case"] = hubsoft_use_case

        # CPF Verification Use Case
        cpf_use_case = CPFVerificationUseCase(
            start_handler=self._instances["start_cpf_verification_handler"],
            submit_handler=self._instances["submit_cpf_verification_handler"],
            cancel_handler=self._instances["cancel_cpf_verification_handler"],
            expire_handler=self._instances["process_expired_verifications_handler"],
            verification_repository=self._instances["cpf_verification_repository"]
        )
        self._instances["cpf_verification_use_case"] = cpf_use_case

        # Admin Operations Use Case
        admin_use_case = AdminOperationsUseCase(
            list_tickets_handler=self._instances["list_tickets_handler"],
            assign_ticket_handler=self._instances["assign_ticket_handler"],
            update_ticket_status_handler=self._instances["update_ticket_status_handler"],
            ban_user_handler=self._instances["ban_user_handler"],
            stats_handler=self._instances["get_system_stats_handler"],
            ticket_repository=self._instances["ticket_repository"],
            user_repository=self._instances["user_repository"],
            verification_repository=self._instances["cpf_verification_repository"]
        )
        self._instances["admin_operations_use_case"] = admin_use_case

        logger.debug("Use cases registrados")

    def get(self, name: str) -> Any:
        """Obtém instância registrada."""
        if not self._initialized:
            raise RuntimeError("Container não foi inicializado. Chame initialize() primeiro.")

        instance = self._instances.get(name)
        if instance is None:
            raise KeyError(f"Dependência '{name}' não foi registrada")

        return instance

    def get_all(self) -> Dict[str, Any]:
        """Obtém todas as instâncias registradas."""
        if not self._initialized:
            raise RuntimeError("Container não foi inicializado")

        return self._instances.copy()

    async def shutdown(self) -> None:
        """Encerra o container e limpa recursos."""
        logger.info("Encerrando Dependency Injection Container...")

        # Encerra serviços que precisam de cleanup
        hubsoft_api = self._instances.get("hubsoft_api_repository")
        if hubsoft_api:
            await hubsoft_api.close()

        cache_manager = self._instances.get("cache_manager")
        if cache_manager:
            await cache_manager.shutdown()

        event_bus = self._instances.get("event_bus")
        if event_bus:
            await event_bus.shutdown()

        self._instances.clear()
        self._initialized = False

        logger.info("Dependency Injection Container encerrado")


# Instância global do container
_container: Optional[DIContainer] = None


async def get_container(config: Optional[Dict[str, Any]] = None) -> DIContainer:
    """Obtém instância global do container."""
    global _container

    if _container is None:
        _container = DIContainer(config)
        await _container.initialize()

    return _container


async def shutdown_container() -> None:
    """Encerra instância global do container."""
    global _container

    if _container is not None:
        await _container.shutdown()
        _container = None