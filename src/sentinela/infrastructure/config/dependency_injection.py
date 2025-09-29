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

    def get(self, interface: Type[T]) -> T:
        """
        Resolve uma dependência.

        Args:
            interface: Interface ou classe a resolver

        Returns:
            T: Instância da dependência

        Raises:
            DependencyNotFoundError: Se dependência não registrada
            DependencyResolutionError: Se erro na criação

        Exemplo:
            user_repo = container.get(UserRepository)
        """
        try:
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
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                # Tenta resolver o tipo
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

    # === Application Layer ===

    # Command handlers
    from ...application.commands.create_user_handler import CreateUserHandler
    from ...application.commands.verify_user_handler import VerifyUserHandler

    container.register_singleton(CreateUserHandler, CreateUserHandler)
    container.register_singleton(VerifyUserHandler, VerifyUserHandler)

    # Query handlers
    from ...application.queries.get_user_handler import GetUserHandler

    container.register_singleton(GetUserHandler, GetUserHandler)

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