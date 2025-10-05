"""
Dependency Injection Container.

Gerencia todas as dependências da aplicação seguindo
os princípios de Inversion of Control (IoC).
"""

import logging
from typing import Dict, Type, TypeVar, Callable, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """
    Dependency Injection Container.

    Gerencia o ciclo de vida e criação de dependências
    da aplicação.
    """

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._aliases: Dict[str, Type] = {}  # Mapeamento nome→tipo para compatibilidade

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """
        Registra uma implementação como singleton.

        Args:
            interface: Interface ou classe abstrata
            implementation: Implementação concreta

        Exemplo:
            container.register_singleton(UserRepository, SQLiteUserRepository)
        """
        self._services[interface] = implementation
        logger.debug(f"Registered singleton: {interface.__name__} -> {implementation.__name__}")

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Registra uma factory para criar instâncias.

        Args:
            interface: Interface ou classe
            factory: Função que cria a instância

        Exemplo:
            container.register_factory(DatabaseConnection, lambda: create_db_connection())
        """
        self._factories[interface] = factory
        logger.debug(f"Registered factory: {interface.__name__}")

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Registra uma instância específica.

        Args:
            interface: Interface ou classe
            instance: Instância já criada

        Exemplo:
            container.register_instance(Config, config_instance)
        """
        self._singletons[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")

    def register_alias(self, name: str, interface: Type[T]) -> None:
        """
        Registra um alias (nome string) para um tipo.

        Permite compatibilidade com código que usa strings para buscar dependências.

        Args:
            name: Nome do alias (string)
            interface: Tipo/Interface correspondente

        Exemplo:
            container.register_alias("user_repository", UserRepository)
            container.get("user_repository")  # Retorna instância de UserRepository
        """
        self._aliases[name] = interface
        logger.debug(f"Registered alias: '{name}' -> {interface.__name__}")

    def get(self, interface_or_name):
        """
        Resolve uma dependência.

        Args:
            interface_or_name: Interface/classe a resolver OU nome string (alias)

        Returns:
            T: Instância da dependência

        Raises:
            DependencyNotFoundError: Se dependência não registrada
            DependencyResolutionError: Se erro na criação

        Exemplos:
            user_repo = container.get(UserRepository)  # Por tipo
            user_repo = container.get("user_repository")  # Por alias
        """
        try:
            # Se for string, resolve via alias
            if isinstance(interface_or_name, str):
                if interface_or_name not in self._aliases:
                    raise DependencyNotFoundError(
                        f"Alias '{interface_or_name}' não registrado. "
                        f"Aliases disponíveis: {list(self._aliases.keys())}"
                    )
                interface = self._aliases[interface_or_name]
            else:
                interface = interface_or_name

            # Verifica se já tem instância singleton
            if interface in self._singletons:
                return self._singletons[interface]

            # Verifica se tem factory registrada
            if interface in self._factories:
                return self._factories[interface]()

            # Verifica se tem implementação para singleton
            if interface in self._services:
                implementation = self._services[interface]

                # Resolve dependências do construtor
                instance = self._create_instance(implementation)

                # Guarda como singleton
                self._singletons[interface] = instance
                return instance

            raise DependencyNotFoundError(f"No registration found for {interface.__name__}")

        except Exception as e:
            if isinstance(e, DependencyNotFoundError):
                raise
            raise DependencyResolutionError(
                f"Error creating instance of {interface.__name__}: {e}",
                original_error=e
            )

    def _create_instance(self, implementation: Type[T]) -> T:
        """
        Cria instância resolvendo dependências do construtor.

        Args:
            implementation: Classe a instanciar

        Returns:
            T: Instância criada
        """
        import inspect

        # Pega assinatura do construtor
        sig = inspect.signature(implementation.__init__)

        # Resolve parâmetros (exceto 'self')
        args = {}

        # Tipos primitivos que não devem ser resolvidos como dependências
        primitive_types = (str, int, float, bool, bytes, type(None))

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                # Ignora tipos primitivos
                if param.annotation in primitive_types:
                    if param.default != inspect.Parameter.empty:
                        continue  # Usa valor padrão
                    else:
                        # Primitivo sem default - erro de configuração
                        raise DependencyResolutionError(
                            f"Parameter '{param_name}' of type '{param.annotation.__name__}' "
                            f"in {implementation.__name__} requires a default value"
                        )

                # Ignora Optional[tipos_primitivos]
                origin = getattr(param.annotation, '__origin__', None)
                if origin is type(None) or str(param.annotation).startswith('typing.Optional'):
                    if param.default != inspect.Parameter.empty:
                        continue

                # Tenta resolver o tipo como dependência
                try:
                    args[param_name] = self.get(param.annotation)
                except DependencyNotFoundError:
                    if param.default != inspect.Parameter.empty:
                        # Usa valor padrão se disponível
                        continue
                    raise

        return implementation(**args)

    def create_scope(self) -> 'DIScope':
        """
        Cria um scope filho que herda registrações do pai.

        Returns:
            DIScope: Novo scope
        """
        return DIScope(parent=self)

    def clear(self) -> None:
        """Limpa todas as registrações e singletons."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._aliases.clear()
        logger.debug("DI Container cleared")


class DIScope(DIContainer):
    """
    Scope de DI que herda do container pai.

    Útil para cenários como request scope, onde você
    quer algumas dependências específicas do contexto.
    """

    def __init__(self, parent: DIContainer):
        super().__init__()
        self._parent = parent

    def get(self, interface: Type[T]) -> T:
        """
        Tenta resolver no scope atual, depois no pai.

        Args:
            interface: Interface a resolver

        Returns:
            T: Instância resolvida
        """
        try:
            return super().get(interface)
        except DependencyNotFoundError:
            return self._parent.get(interface)


class DependencyNotFoundError(Exception):
    """Dependência não encontrada no container."""
    pass


class DependencyResolutionError(Exception):
    """Erro ao resolver/criar dependência."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


# Container global da aplicação
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Retorna o container global da aplicação.

    Returns:
        DIContainer: Container global
    """
    global _global_container
    if _global_container is None:
        _global_container = DIContainer()
    return _global_container


def configure_dependencies() -> None:
    """
    Configura todas as dependências da aplicação.

    Esta função deve ser chamada na inicialização
    para registrar todas as implementações.
    """
    container = get_container()

    # Limpa configurações anteriores
    container.clear()

    logger.info("Configurando dependências...")

    # === Infrastructure Layer ===

    # Repositories
    from ...domain.repositories.user_repository import UserRepository
    from ..repositories.sqlite_user_repository import SQLiteUserRepository
    from ...core.config import DATABASE_FILE

    # Register repository with database path via factory
    def create_user_repository() -> SQLiteUserRepository:
        return SQLiteUserRepository(DATABASE_FILE)

    container.register_factory(UserRepository, create_user_repository)

    # Admin Repository
    from ...domain.repositories.admin_repository import AdminRepository
    from ..repositories.sqlite_admin_repository import SQLiteAdminRepository

    def create_admin_repository() -> SQLiteAdminRepository:
        return SQLiteAdminRepository(DATABASE_FILE)

    container.register_factory(AdminRepository, create_admin_repository)

    # === External Services ===

    # HubSoft services
    from ..external_services.hubsoft_client import HubSoftClient
    from ..external_services.hubsoft_client_impl import HubSoftClientImpl
    from ..external_services.group_client import GroupClient
    from ..external_services.group_client_impl import GroupClientImpl
    from ..external_services.invite_client import InviteClient
    from ..external_services.invite_client_impl import InviteClientImpl

    container.register_singleton(HubSoftClient, HubSoftClientImpl)
    container.register_singleton(GroupClient, GroupClientImpl)
    container.register_singleton(InviteClient, InviteClientImpl)

    # === Event System ===

    # Event Bus
    from ..events.event_bus import EventBus, InMemoryEventBus
    container.register_singleton(EventBus, InMemoryEventBus)

    # === Application Layer ===

    # Command handlers
    from ...application.commands.create_user_handler import CreateUserHandler
    from ...application.commands.verify_user_handler import VerifyUserHandler

    container.register_singleton(CreateUserHandler, CreateUserHandler)
    container.register_singleton(VerifyUserHandler, VerifyUserHandler)

    # Query handlers
    from ...application.queries.get_user_handler import GetUserHandler

    container.register_singleton(GetUserHandler, GetUserHandler)

    # === Repositories (Additional) ===

    # CPF Verification Repository
    from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
    from ..repositories.sqlite_cpf_verification_repository import SQLiteCPFVerificationRepository

    def create_cpf_verification_repository() -> SQLiteCPFVerificationRepository:
        return SQLiteCPFVerificationRepository(DATABASE_FILE)

    container.register_factory(CPFVerificationRepository, create_cpf_verification_repository)

    # Ticket Repository
    from ...domain.repositories.ticket_repository import TicketRepository
    from ..repositories.sqlite_ticket_repository import SQLiteTicketRepository

    def create_ticket_repository() -> SQLiteTicketRepository:
        return SQLiteTicketRepository(DATABASE_FILE)

    container.register_factory(TicketRepository, create_ticket_repository)

    # HubSoft Integration Repository
    from ...domain.repositories.hubsoft_repository import HubSoftIntegrationRepository
    from ..repositories.sqlite_hubsoft_integration_repository import SQLiteHubSoftIntegrationRepository

    def create_hubsoft_integration_repository() -> SQLiteHubSoftIntegrationRepository:
        return SQLiteHubSoftIntegrationRepository(DATABASE_FILE)

    container.register_factory(HubSoftIntegrationRepository, create_hubsoft_integration_repository)

    # Group Member Repository
    from ...domain.repositories.group_member_repository import GroupMemberRepository
    from ..repositories.sqlite_group_member_repository import SQLiteGroupMemberRepository

    def create_group_member_repository() -> SQLiteGroupMemberRepository:
        return SQLiteGroupMemberRepository(DATABASE_FILE)

    container.register_factory(GroupMemberRepository, create_group_member_repository)

    # === Command Handlers ===

    # HubSoft Handlers
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

    container.register_singleton(ScheduleHubSoftIntegrationHandler, ScheduleHubSoftIntegrationHandler)
    container.register_singleton(SyncTicketToHubSoftHandler, SyncTicketToHubSoftHandler)
    container.register_singleton(VerifyUserInHubSoftHandler, VerifyUserInHubSoftHandler)
    container.register_singleton(BulkSyncTicketsToHubSoftHandler, BulkSyncTicketsToHubSoftHandler)
    container.register_singleton(RetryFailedIntegrationsHandler, RetryFailedIntegrationsHandler)
    container.register_singleton(CancelHubSoftIntegrationHandler, CancelHubSoftIntegrationHandler)
    container.register_singleton(UpdateIntegrationPriorityHandler, UpdateIntegrationPriorityHandler)
    container.register_singleton(GetHubSoftIntegrationStatusHandler, GetHubSoftIntegrationStatusHandler)

    # CPF Verification Handlers
    from ...application.command_handlers.cpf_verification_handlers import (
        StartCPFVerificationHandler,
        SubmitCPFForVerificationHandler,
        CancelCPFVerificationHandler
    )
    from ...application.command_handlers.process_expired_verifications_handler import (
        ProcessExpiredVerificationsHandler
    )
    from ...application.command_handlers.resolve_cpf_duplicate_handler import (
        ResolveCPFDuplicateHandler
    )

    container.register_singleton(StartCPFVerificationHandler, StartCPFVerificationHandler)
    container.register_singleton(SubmitCPFForVerificationHandler, SubmitCPFForVerificationHandler)
    container.register_singleton(CancelCPFVerificationHandler, CancelCPFVerificationHandler)
    container.register_singleton(ProcessExpiredVerificationsHandler, ProcessExpiredVerificationsHandler)
    container.register_singleton(ResolveCPFDuplicateHandler, ResolveCPFDuplicateHandler)

    # Admin Handlers
    from ...application.command_handlers.admin_command_handlers import (
        ListTicketsHandler,
        AssignTicketHandler,
        UpdateTicketStatusHandler,
        BanUserHandler,
        GetSystemStatsHandler
    )

    container.register_singleton(ListTicketsHandler, ListTicketsHandler)
    container.register_singleton(AssignTicketHandler, AssignTicketHandler)
    container.register_singleton(UpdateTicketStatusHandler, UpdateTicketStatusHandler)
    container.register_singleton(BanUserHandler, BanUserHandler)
    container.register_singleton(GetSystemStatsHandler, GetSystemStatsHandler)

    # === Domain Services ===

    from ...domain.services.cpf_validation_service import CPFValidationService
    from ...domain.services.duplicate_cpf_service import DuplicateCPFService

    container.register_singleton(CPFValidationService, CPFValidationService)
    container.register_singleton(DuplicateCPFService, DuplicateCPFService)

    # === External Services (HubSoft API) ===

    from ...domain.repositories.hubsoft_repository import HubSoftAPIRepository, HubSoftCacheRepository
    from ..external_services.hubsoft_api_service import HubSoftAPIService, HubSoftCacheService
    from ...core.config import HUBSOFT_HOST, HUBSOFT_USER, HUBSOFT_PASSWORD
    import os

    # Factory para HubSoftAPIService com configurações
    def create_hubsoft_api_service() -> HubSoftAPIService:
        return HubSoftAPIService(
            base_url=HUBSOFT_HOST or os.getenv("HUBSOFT_HOST", "https://api.hubsoft.com.br"),
            username=HUBSOFT_USER or os.getenv("HUBSOFT_USER", ""),
            password=HUBSOFT_PASSWORD or os.getenv("HUBSOFT_PASSWORD", ""),
            timeout_seconds=int(os.getenv("HUBSOFT_TIMEOUT", "30"))
        )

    # Factory para HubSoftCacheService
    def create_hubsoft_cache_service() -> HubSoftCacheService:
        return HubSoftCacheService()

    container.register_factory(HubSoftAPIRepository, create_hubsoft_api_service)
    container.register_factory(HubSoftCacheRepository, create_hubsoft_cache_service)

    # === Use Cases ===

    # CPF Verification Use Case
    from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
    container.register_singleton(CPFVerificationUseCase, CPFVerificationUseCase)

    # HubSoft Integration Use Case
    from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
    container.register_singleton(HubSoftIntegrationUseCase, HubSoftIntegrationUseCase)

    # Admin Operations Use Case
    from ...application.use_cases.admin_operations_use_case import AdminOperationsUseCase
    container.register_singleton(AdminOperationsUseCase, AdminOperationsUseCase)

    # Member Verification Use Case
    from ...application.use_cases.member_verification_use_case import MemberVerificationUseCase
    container.register_singleton(MemberVerificationUseCase, MemberVerificationUseCase)

    # Welcome Management Use Case
    from ...application.use_cases.welcome_management_use_case import WelcomeManagementUseCase
    from ...core.config import TELEGRAM_GROUP_ID, WELCOME_TOPIC_ID, RULES_TOPIC_ID

    def create_welcome_management_use_case() -> WelcomeManagementUseCase:
        user_repo = container.get(UserRepository)
        member_repo = container.get(GroupMemberRepository)
        event_bus = container.get(EventBus)

        return WelcomeManagementUseCase(
            user_repository=user_repo,
            member_repository=member_repo,
            event_bus=event_bus,
            group_id=int(TELEGRAM_GROUP_ID),
            welcome_topic_id=int(WELCOME_TOPIC_ID) if WELCOME_TOPIC_ID else None,
            rules_topic_id=int(RULES_TOPIC_ID) if RULES_TOPIC_ID else None,
            rules_acceptance_hours=24
        )

    container.register_factory(WelcomeManagementUseCase, create_welcome_management_use_case)

    # === String Aliases (Compatibilidade com código legado) ===

    # Repositories
    container.register_alias("user_repository", UserRepository)
    container.register_alias("admin_repository", AdminRepository)
    container.register_alias("cpf_verification_repository", CPFVerificationRepository)
    container.register_alias("ticket_repository", TicketRepository)
    container.register_alias("hubsoft_integration_repository", HubSoftIntegrationRepository)
    container.register_alias("group_member_repository", GroupMemberRepository)

    # Use Cases
    container.register_alias("cpf_verification_use_case", CPFVerificationUseCase)
    container.register_alias("hubsoft_integration_use_case", HubSoftIntegrationUseCase)
    container.register_alias("admin_operations_use_case", AdminOperationsUseCase)
    container.register_alias("member_verification_use_case", MemberVerificationUseCase)
    container.register_alias("welcome_management_use_case", WelcomeManagementUseCase)

    # === Event System ===

    # Registra event handlers no EventBus
    logger.info("🔧 Registering event handlers...")
    try:
        from ..events.event_handler_registry import EventHandlerRegistry
        from ..events.event_bus import EventBus

        event_bus = container.get(EventBus)
        registry = EventHandlerRegistry(event_bus)
        registry.register_all_handlers()
        logger.info("✅ Event handlers registered successfully")
    except Exception as e:
        logger.error(f"⚠️ Failed to register event handlers: {e}")
        # Não falha a configuração por event handlers (sistema pode funcionar sem eventos)

    logger.info("Dependências configuradas com sucesso")


def dependency_injected(func: Callable) -> Callable:
    """
    Decorator para injeção automática de dependências.

    Analisa os type hints da função e injeta automaticamente
    as dependências registradas no container.

    Exemplo:
        @dependency_injected
        async def create_user(user_repo: UserRepository, data: dict):
            # user_repo será injetado automaticamente
            pass
    """
    import inspect
    from functools import wraps

    sig = inspect.signature(func)
    container = get_container()

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Resolve dependências baseadas nos type hints
        for param_name, param in sig.parameters.items():
            if (param_name not in kwargs and
                param.annotation != inspect.Parameter.empty and
                hasattr(param.annotation, '__origin__') is False):  # Não é generic type

                try:
                    dependency = container.get(param.annotation)
                    kwargs[param_name] = dependency
                except DependencyNotFoundError:
                    # Se não conseguir resolver, deixa como está
                    # (pode ser passado manualmente)
                    pass

        return await func(*args, **kwargs)

    return wrapper