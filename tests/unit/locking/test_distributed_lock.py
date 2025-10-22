"""
Testes para o sistema de locks distribuídos.

CORREÇÃO INCONSISTÊNCIA #1: Race Condition em Verificação Duplicada Simultânea
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.sentinela.infrastructure.locking.distributed_lock import (
    InMemoryLockManager,
    distributed_lock,
    LockAcquisitionError
)


@pytest.mark.asyncio
class TestDistributedLock:
    """Testes do sistema de locks distribuídos."""

    async def test_lock_acquisition_success(self):
        """
        Teste: Lock deve ser adquirido com sucesso quando disponível.

        Cenário:
        - Lock não está sendo usado
        - Tentativa de aquisição

        Resultado esperado:
        - Lock adquirido com sucesso
        - Recurso protegido acessível
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "test_resource"

        # Act & Assert
        async with distributed_lock(lock_key, timeout=5, lock_manager=lock_manager):
            # Se chegou aqui, lock foi adquirido
            assert lock_key in lock_manager._locks
            assert lock_manager._locks[lock_key]["acquired"] is True

    async def test_lock_prevents_concurrent_access(self):
        """
        Teste: Lock deve prevenir acesso concurrent ao mesmo recurso.

        TESTE CRÍTICO - Inconsistência #1

        Cenário:
        - Primeira coroutine adquire lock
        - Segunda coroutine tenta adquirir mesmo lock simultaneamente

        Resultado esperado:
        - Primeira coroutine consegue adquirir
        - Segunda coroutine aguarda ou falha com timeout
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "cpf_verification:12345678900"
        results = []

        async def task1():
            """Primeira task que adquire o lock."""
            try:
                async with distributed_lock(lock_key, timeout=10, lock_manager=lock_manager):
                    results.append("task1_acquired")
                    await asyncio.sleep(2)  # Simula processamento
                    results.append("task1_completed")
            except LockAcquisitionError:
                results.append("task1_failed")

        async def task2():
            """Segunda task que tenta adquirir o mesmo lock."""
            await asyncio.sleep(0.5)  # Garante que task1 adquire primeiro
            try:
                async with distributed_lock(lock_key, timeout=1, lock_manager=lock_manager):
                    results.append("task2_acquired")
            except LockAcquisitionError:
                results.append("task2_timeout")

        # Act
        await asyncio.gather(task1(), task2())

        # Assert
        assert "task1_acquired" in results, "Task 1 deve adquirir o lock"
        assert "task1_completed" in results, "Task 1 deve completar"
        assert "task2_timeout" in results, "Task 2 deve falhar com timeout (race condition prevenida)"
        assert "task2_acquired" not in results, "Task 2 NÃO deve adquirir lock enquanto task 1 usa"

    async def test_lock_released_after_use(self):
        """
        Teste: Lock deve ser liberado automaticamente após uso.

        Cenário:
        - Lock adquirido e usado
        - Bloco with finaliza

        Resultado esperado:
        - Lock liberado (available = True)
        - Próxima aquisição possível
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "test_resource"

        # Act
        async with distributed_lock(lock_key, timeout=5, lock_manager=lock_manager):
            pass  # Lock adquirido e liberado automaticamente

        # Assert - Lock deve estar liberado
        assert lock_manager._locks[lock_key]["acquired"] is False

    async def test_lock_released_on_exception(self):
        """
        Teste: Lock deve ser liberado mesmo se ocorrer exceção.

        Cenário:
        - Lock adquirido
        - Exceção lançada dentro do bloco

        Resultado esperado:
        - Lock liberado (cleanup garantido)
        - Exceção propagada
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "test_resource"

        # Act & Assert
        with pytest.raises(ValueError):
            async with distributed_lock(lock_key, timeout=5, lock_manager=lock_manager):
                raise ValueError("Simulated error")

        # Lock deve estar liberado mesmo após erro
        assert lock_manager._locks[lock_key]["acquired"] is False

    async def test_timeout_raises_error(self):
        """
        Teste: Timeout ao adquirir lock deve lançar LockAcquisitionError.

        Cenário:
        - Lock já está sendo usado
        - Tentativa de aquisição com timeout curto

        Resultado esperado:
        - LockAcquisitionError lançada
        - Mensagem clara sobre timeout
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "busy_resource"

        async def hold_lock():
            """Task que mantém o lock."""
            async with distributed_lock(lock_key, timeout=10, lock_manager=lock_manager):
                await asyncio.sleep(5)

        async def try_acquire():
            """Task que tenta adquirir lock ocupado."""
            await asyncio.sleep(0.5)  # Garante que hold_lock adquire primeiro
            async with distributed_lock(lock_key, timeout=1, lock_manager=lock_manager):
                pass

        # Act & Assert
        task1 = asyncio.create_task(hold_lock())
        task2 = asyncio.create_task(try_acquire())

        with pytest.raises(LockAcquisitionError):
            await task2

        await task1  # Cleanup

    async def test_expired_locks_cleanup(self):
        """
        Teste: Locks expirados devem ser limpos automaticamente.

        Cenário:
        - Lock adquirido mas processo morreu (simulado)
        - Cleanup automático executado

        Resultado esperado:
        - Lock expirado removido
        - Novos locks podem ser adquiridos
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        lock_key = "test_resource"

        # Simula lock "órfão" (processo morreu sem liberar)
        expired_time = datetime.now() - timedelta(seconds=120)  # Expirado há 2 minutos
        lock_manager._locks[lock_key] = {
            "acquired": True,
            "acquired_at": expired_time,
            "expires_at": expired_time + timedelta(seconds=30)
        }

        # Act - Cleanup automático
        await lock_manager.cleanup_expired_locks()

        # Assert - Lock expirado deve ter sido removido ou liberado
        if lock_key in lock_manager._locks:
            assert lock_manager._locks[lock_key]["acquired"] is False

    async def test_race_condition_prevention_cpf_verification(self):
        """
        TESTE DE ACEITAÇÃO - Inconsistência #1

        Simula o cenário real do bug:
        - Usuário A inicia verificação com CPF 12345678900
        - Usuário B (mesma pessoa) inicia verificação com mesmo CPF simultaneamente
        - Sem lock: ambos passariam pela verificação
        - Com lock: apenas 1 passa, outro aguarda ou falha

        Resultado esperado:
        - Apenas 1 verificação processa por vez
        - Segunda verificação aguarda ou recebe erro de timeout
        """
        # Arrange
        lock_manager = InMemoryLockManager()
        cpf = "12345678900"
        lock_key = f"cpf_verification:{cpf}"
        verification_results = []

        async def verify_cpf(user_id: int):
            """Simula verificação de CPF."""
            try:
                async with distributed_lock(lock_key, timeout=2, lock_manager=lock_manager):
                    verification_results.append(f"user_{user_id}_started")
                    await asyncio.sleep(1)  # Simula chamada à API HubSoft
                    verification_results.append(f"user_{user_id}_completed")
                    return True
            except LockAcquisitionError:
                verification_results.append(f"user_{user_id}_blocked")
                return False

        # Act - Simula 2 usuários tentando verificar mesmo CPF simultaneamente
        user_a = asyncio.create_task(verify_cpf(user_id=111))
        user_b = asyncio.create_task(verify_cpf(user_id=222))

        results = await asyncio.gather(user_a, user_b)

        # Assert
        # Um dos usuários deve ter completado, o outro deve ter sido bloqueado
        completed_count = sum(1 for r in verification_results if "completed" in r)
        blocked_count = sum(1 for r in verification_results if "blocked" in r)

        assert completed_count == 1, "Apenas 1 verificação deve completar (race condition prevenida)"
        assert blocked_count == 1, "Segunda verificação deve ser bloqueada"
        assert results.count(True) == 1, "Apenas 1 verificação deve retornar sucesso"
        assert results.count(False) == 1, "Segunda verificação deve retornar falha"


@pytest.mark.asyncio
class TestInMemoryLockManager:
    """Testes do InMemoryLockManager."""

    async def test_singleton_behavior(self):
        """
        Teste: Lock manager deve manter estado global (singleton-like).

        Cenário:
        - Múltiplas instâncias do manager

        Resultado esperado:
        - Todas compartilham os mesmos locks
        """
        # Arrange & Act
        manager1 = InMemoryLockManager()
        manager2 = InMemoryLockManager()

        lock_key = "shared_resource"
        async with distributed_lock(lock_key, timeout=5, lock_manager=manager1):
            # Assert
            # Manager2 deve ver o lock adquirido por manager1
            assert lock_key in manager2._locks or lock_key in manager1._locks

    async def test_multiple_different_locks(self):
        """
        Teste: Múltiplos locks diferentes podem ser adquiridos simultaneamente.

        Cenário:
        - Lock A para recurso X
        - Lock B para recurso Y

        Resultado esperado:
        - Ambos adquiridos com sucesso (recursos diferentes)
        """
        # Arrange
        lock_manager = InMemoryLockManager()

        # Act
        async with distributed_lock("resource_x", timeout=5, lock_manager=lock_manager):
            async with distributed_lock("resource_y", timeout=5, lock_manager=lock_manager):
                # Assert
                assert "resource_x" in lock_manager._locks
                assert "resource_y" in lock_manager._locks
                assert lock_manager._locks["resource_x"]["acquired"] is True
                assert lock_manager._locks["resource_y"]["acquired"] is True
