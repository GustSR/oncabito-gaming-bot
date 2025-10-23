"""
Sistema de lock distribuído para prevenção de race conditions.

Implementa locks em nível de aplicação para garantir que operações
críticas não sejam executadas simultaneamente.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class InMemoryLockManager:
    """
    Gerenciador de locks em memória.

    NOTA: Esta implementação é adequada para deployments single-instance.
    Para ambientes multi-instance (múltiplos workers), considere usar
    Redis ou outro sistema de lock distribuído.
    """

    def __init__(self):
        self._locks: dict[str, tuple[asyncio.Lock, datetime]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def __del__(self):
        """Garante que a task de cleanup seja cancelada ao destruir o objeto."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            # Tenta aguardar o cancelamento para evitar warning
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(asyncio.sleep(0))
            except:
                pass  # Ignora erros no destrutor

    async def start(self):
        """Inicia o gerenciador de locks."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_locks())
            logger.info("InMemoryLockManager iniciado")

    async def stop(self):
        """Para o gerenciador de locks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("InMemoryLockManager parado")

    async def _cleanup_expired_locks(self):
        """Remove locks expirados periodicamente."""
        try:
            while True:
                try:
                    await asyncio.sleep(60)  # Executa a cada minuto
                    now = datetime.now()
                    expired_keys = [
                        key for key, (_, expires_at) in self._locks.items()
                        if expires_at < now
                    ]
                    for key in expired_keys:
                        del self._locks[key]
                        logger.debug(f"Lock expirado removido: {key}")
                except asyncio.CancelledError:
                    logger.debug("Cleanup de locks cancelado (shutdown)")
                    break
                except Exception as e:
                    logger.error(f"Erro ao limpar locks expirados: {e}")
        finally:
            # Garante que não haverá warning de "Task was destroyed"
            pass

    @asynccontextmanager
    async def acquire(self, key: str, timeout: int = 30):
        """
        Adquire um lock para a chave especificada.

        Args:
            key: Identificador único do recurso a ser bloqueado
            timeout: Tempo máximo de espera em segundos

        Raises:
            asyncio.TimeoutError: Se não conseguir adquirir o lock no tempo limite

        Example:
            async with lock_manager.acquire("cpf:12345678900", timeout=30):
                # Operação crítica aqui
                pass
        """
        # Cria ou obtém o lock para esta chave
        if key not in self._locks:
            self._locks[key] = (asyncio.Lock(), datetime.now() + timedelta(seconds=timeout + 60))

        lock, expires_at = self._locks[key]

        # Atualiza o tempo de expiração
        self._locks[key] = (lock, datetime.now() + timedelta(seconds=timeout + 60))

        logger.debug(f"Tentando adquirir lock: {key} (timeout: {timeout}s)")

        try:
            # Tenta adquirir o lock com timeout
            # Usa wait_for para compatibilidade com Python 3.10+
            await asyncio.wait_for(lock.acquire(), timeout=timeout)

            logger.debug(f"Lock adquirido: {key}")

            try:
                yield
            finally:
                lock.release()
                logger.debug(f"Lock liberado: {key}")

        except asyncio.TimeoutError:
            logger.warning(f"Timeout ao tentar adquirir lock: {key} após {timeout}s")
            raise
        except Exception as e:
            logger.error(f"Erro ao gerenciar lock {key}: {e}")
            raise


# Singleton global
_global_lock_manager: Optional[InMemoryLockManager] = None


def get_lock_manager() -> InMemoryLockManager:
    """
    Obtém a instância global do gerenciador de locks.

    Returns:
        InMemoryLockManager: Instância global do gerenciador
    """
    global _global_lock_manager
    if _global_lock_manager is None:
        _global_lock_manager = InMemoryLockManager()
    return _global_lock_manager


@asynccontextmanager
async def distributed_lock(key: str, timeout: int = 30):
    """
    Context manager para adquirir um lock distribuído.

    Args:
        key: Identificador único do recurso
        timeout: Tempo máximo de espera em segundos

    Example:
        async with distributed_lock("cpf:12345678900", timeout=30):
            # Código crítico aqui
            pass
    """
    manager = get_lock_manager()
    async with manager.acquire(key, timeout):
        yield
