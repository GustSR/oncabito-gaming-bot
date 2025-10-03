"""
Bootstrap da aplicação.

Inicializa e configura toda a nova arquitetura.
"""

import logging
import asyncio
from typing import Optional

from .dependency_injection import configure_dependencies, get_container
from ...domain.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class ApplicationBootstrap:
    """
    Bootstrap da aplicação.

    Responsável por:
    - Configurar dependências
    - Inicializar infraestrutura
    - Verificar saúde do sistema
    - Preparar para operação
    """

    def __init__(self):
        self._is_initialized = False

    async def initialize(self) -> None:
        """
        Inicializa a aplicação.

        Raises:
            BootstrapError: Se erro na inicialização
        """
        if self._is_initialized:
            logger.warning("Application already initialized")
            return

        logger.info("🚀 Initializing application with new architecture...")

        try:
            # 1. Configurar dependências
            await self._configure_dependencies()

            # 2. Verificar infraestrutura
            await self._verify_infrastructure()

            # 3. Executar migrations se necessário
            await self._run_migrations()

            # 4. Verificar saúde do sistema
            await self._health_check()

            self._is_initialized = True
            logger.info("✅ Application initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize application: {e}")
            raise BootstrapError(f"Initialization failed: {e}") from e

    async def _configure_dependencies(self) -> None:
        """Configura todas as dependências."""
        logger.info("📦 Configuring dependencies...")

        try:
            configure_dependencies()
            container = get_container()

            # Verifica se dependências críticas foram registradas
            critical_deps = [UserRepository]

            for dep in critical_deps:
                try:
                    instance = container.get(dep)
                    logger.debug(f"✅ {dep.__name__}: {instance.__class__.__name__}")
                except Exception as e:
                    raise BootstrapError(f"Failed to resolve {dep.__name__}: {e}")

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
                # Não falha bootstrap por event handlers (sistema pode funcionar sem eventos)

            logger.info("✅ Dependencies configured successfully")

        except Exception as e:
            raise BootstrapError(f"Dependency configuration failed: {e}") from e

    async def _verify_infrastructure(self) -> None:
        """Verifica se infraestrutura está disponível."""
        logger.info("🔍 Verifying infrastructure...")

        try:
            container = get_container()

            # Testa repository
            user_repo = container.get(UserRepository)

            # Testa conexão com banco (tentativa de operação simples)
            await user_repo.count_active_users()

            logger.info("✅ Infrastructure verified successfully")

        except Exception as e:
            raise BootstrapError(f"Infrastructure verification failed: {e}") from e

    async def _run_migrations(self) -> None:
        """Executa migrations se necessário."""
        logger.info("🔄 Checking for migrations...")

        try:
            # Por enquanto, só log - migrations serão implementadas depois
            logger.info("ℹ️ Migration system not yet implemented")

        except Exception as e:
            logger.warning(f"Migration check failed: {e}")

    async def _health_check(self) -> None:
        """Executa health check do sistema."""
        logger.info("🏥 Running health check...")

        try:
            container = get_container()

            # Verifica cada componente crítico
            user_repo = container.get(UserRepository)

            # Health check básico
            count = await user_repo.count_active_users()
            logger.info(f"📊 Active users: {count}")

            logger.info("✅ Health check passed")

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            # Não falha a inicialização por health check

    def is_initialized(self) -> bool:
        """
        Verifica se aplicação foi inicializada.

        Returns:
            bool: True se inicializada
        """
        return self._is_initialized


class BootstrapError(Exception):
    """Erro na inicialização da aplicação."""
    pass


# Instância global do bootstrap
_bootstrap: Optional[ApplicationBootstrap] = None


def get_bootstrap() -> ApplicationBootstrap:
    """
    Retorna instância global do bootstrap.

    Returns:
        ApplicationBootstrap: Instância do bootstrap
    """
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = ApplicationBootstrap()
    return _bootstrap


async def initialize_application() -> None:
    """
    Função de conveniência para inicializar a aplicação.

    Raises:
        BootstrapError: Se erro na inicialização
    """
    bootstrap = get_bootstrap()
    await bootstrap.initialize()


def is_application_initialized() -> bool:
    """
    Verifica se aplicação foi inicializada.

    Returns:
        bool: True se inicializada
    """
    global _bootstrap
    return _bootstrap is not None and _bootstrap.is_initialized()


# Decorator para garantir que aplicação está inicializada
def require_initialized(func):
    """
    Decorator que garante que aplicação foi inicializada.

    Args:
        func: Função a decorar

    Returns:
        Função decorada

    Raises:
        RuntimeError: Se aplicação não inicializada
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not is_application_initialized():
            raise RuntimeError(
                "Application not initialized. Call initialize_application() first."
            )
        return await func(*args, **kwargs)

    return wrapper