"""
Testes para o sistema de locks distribuídos.

CORREÇÃO INCONSISTÊNCIA #1: Race Condition em Verificação Duplicada Simultânea
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from src.sentinela.infrastructure.locking.distributed_lock import (
    InMemoryLockManager,
    distributed_lock
)


@pytest.mark.asyncio
class TestDistributedLock:
    """Testes do sistema de locks distribuídos."""

    async def test_lock_prevents_concurrent_access(self):
        """
        Teste: Lock deve prevenir acesso concorrente ao mesmo recurso.

        TESTE CRÍTICO - Inconsistência #1

        Cenário:
        - Primeira coroutine adquire lock
        - Segunda coroutine tenta adquirir mesmo lock simultaneamente

        Resultado esperado:
        - Primeira coroutine consegue adquirir
        - Segunda coroutine aguarda ou falha com timeout
        """
        # Arrange
        lock_key = "cpf_verification:12345678900"
        results = []

        async def task1():
            """Primeira task que adquire o lock."""
            try:
                async with distributed_lock(lock_key, timeout=10):
                    results.append("task1_acquired")
                    await asyncio.sleep(2)  # Simula processamento
                    results.append("task1_completed")
            except asyncio.TimeoutError:
                results.append("task1_failed")

        async def task2():
            """Segunda task que tenta adquirir o mesmo lock."""
            await asyncio.sleep(0.5)  # Garante que task1 adquire primeiro
            try:
                async with distributed_lock(lock_key, timeout=1):
                    results.append("task2_acquired")
            except asyncio.TimeoutError:
                results.append("task2_timeout")

        # Act
        await asyncio.gather(task1(), task2())

        # Assert
        assert "task1_acquired" in results, "Task 1 deve adquirir o lock"
        assert "task1_completed" in results, "Task 1 deve completar"
        assert "task2_timeout" in results, "Task 2 deve falhar com timeout (race condition prevenida)"
        assert "task2_acquired" not in results, "Task 2 NÃO deve adquirir lock enquanto task 1 usa"

    async def test_timeout_raises_error(self):
        """
        Teste: Timeout ao adquirir lock deve lançar asyncio.TimeoutError.

        Cenário:
        - Lock já está sendo usado
        - Tentativa de aquisição com timeout curto

        Resultado esperado:
        - asyncio.TimeoutError lançada
        - Mensagem clara sobre timeout
        """
        # Arrange
        lock_key = "busy_resource"

        async def hold_lock():
            """Task que mantém o lock."""
            async with distributed_lock(lock_key, timeout=10):
                await asyncio.sleep(5)

        async def try_acquire():
            """Task que tenta adquirir lock ocupado."""
            await asyncio.sleep(0.5)  # Garante que hold_lock adquire primeiro
            with pytest.raises(asyncio.TimeoutError):
                async with distributed_lock(lock_key, timeout=1):
                    pass  # Não deve chegar aqui

        # Act & Assert
        await asyncio.gather(hold_lock(), try_acquire())

    async def test_lock_cleanup_after_exception(self):
        """
        Teste: Lock deve ser liberado após cleanup de exceções.

        Cenário:
        - Lock adquirido
        - Exceção ocorre dentro do lock
        - Lock é liberado pelo cleanup

        Resultado esperado:
        - Próxima tentativa consegue adquirir o lock
        """
        # Arrange
        lock_key = "cleanup_test"

        # Act 1: Adquire lock e lança exceção
        try:
            async with distributed_lock(lock_key, timeout=5):
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Esperado

        # Act 2: Deve conseguir adquirir novamente (lock foi liberado)
        acquired = False
        async with distributed_lock(lock_key, timeout=5):
            acquired = True

        # Assert
        assert acquired, "Lock deve ser adquirido após cleanup"

    @pytest.mark.inconsistency1
    async def test_race_condition_prevention_cpf_verification(self):
        """
        TESTE DE ACEITAÇÃO - Inconsistência #1

        Simula o cenário real do bug:
        - Usuário A inicia verificação com CPF 12345678900
        - Usuário B (mesma pessoa) inicia verificação com mesmo CPF simultaneamente
        - Sem lock: ambos passariam pela verificação
        - Com lock: apenas 1 passa, outro aguarda ou falha
        """
        # Arrange
        cpf = "12345678900"
        lock_key = f"cpf_verification:{cpf}"
        verification_results = []

        async def verify_cpf(user_id: int):
            """Simula verificação de CPF."""
            try:
                async with distributed_lock(lock_key, timeout=2):
                    verification_results.append(f"user_{user_id}_started")
                    await asyncio.sleep(1)  # Simula processamento
                    verification_results.append(f"user_{user_id}_completed")
                    return True
            except asyncio.TimeoutError:
                verification_results.append(f"user_{user_id}_blocked")
                return False

        # Act: Simula 2 usuários tentando verificar mesmo CPF simultaneamente
        user_a = asyncio.create_task(verify_cpf(user_id=111))
        user_b = asyncio.create_task(verify_cpf(user_id=222))
        results = await asyncio.gather(user_a, user_b)

        # Assert
        completed_count = sum(1 for r in verification_results if "completed" in r)
        blocked_count = sum(1 for r in verification_results if "blocked" in r)

        assert completed_count == 1, "Apenas 1 verificação deve completar"
        assert blocked_count == 1, "Segunda verificação deve ser bloqueada"
        assert True in results and False in results, "Um sucesso e uma falha"

    async def test_lock_different_resources_concurrent(self):
        """
        Teste: Locks de recursos diferentes não devem bloquear uns aos outros.

        Cenário:
        - Task 1 adquire lock para recurso A
        - Task 2 adquire lock para recurso B (diferente)

        Resultado esperado:
        - Ambas as tasks executam simultaneamente
        """
        # Arrange
        results = []

        async def access_resource_a():
            async with distributed_lock("resource_a", timeout=5):
                results.append("a_acquired")
                await asyncio.sleep(1)
                results.append("a_completed")

        async def access_resource_b():
            async with distributed_lock("resource_b", timeout=5):
                results.append("b_acquired")
                await asyncio.sleep(1)
                results.append("b_completed")

        # Act
        await asyncio.gather(access_resource_a(), access_resource_b())

        # Assert
        assert "a_acquired" in results
        assert "a_completed" in results
        assert "b_acquired" in results
        assert "b_completed" in results

    async def test_lock_nested_same_resource_deadlock(self):
        """
        Teste: Lock aninhado no mesmo recurso causa deadlock.

        Cenário:
        - Dentro de um lock, tenta adquirir o mesmo lock novamente

        Resultado esperado:
        - Timeout (deadlock detectado)
        """
        # Arrange
        lock_key = "same_resource"

        # Act & Assert
        with pytest.raises(asyncio.TimeoutError):
            async with distributed_lock(lock_key, timeout=2):
                # Tenta adquirir novamente (deadlock)
                async with distributed_lock(lock_key, timeout=1):
                    pass  # Nunca deve chegar aqui


@pytest.mark.asyncio
class TestInMemoryLockManager:
    """Testes diretos do InMemoryLockManager."""

    async def test_manager_acquire_and_release(self):
        """
        Teste: Lock manager deve adquirir e liberar locks corretamente.
        """
        # Arrange
        manager = InMemoryLockManager()
        lock_key = "test_lock"

        # Act & Assert
        async with manager.acquire(lock_key, timeout=5):
            # Lock adquirido
            assert lock_key in manager._locks

        # Lock ainda existe (será limpo pelo cleanup periódico)
        assert lock_key in manager._locks

    async def test_manager_concurrent_locks(self):
        """
        Teste: Manager deve gerenciar locks concorrentes corretamente.
        """
        # Arrange
        manager = InMemoryLockManager()
        lock_key = "concurrent_test"
        results = []

        async def task1():
            async with manager.acquire(lock_key, timeout=10):
                results.append("task1_start")
                await asyncio.sleep(1)
                results.append("task1_end")

        async def task2():
            await asyncio.sleep(0.3)
            try:
                async with manager.acquire(lock_key, timeout=0.5):
                    results.append("task2_acquired")
            except asyncio.TimeoutError:
                results.append("task2_timeout")

        # Act
        await asyncio.gather(task1(), task2())

        # Assert
        assert "task1_start" in results
        assert "task1_end" in results
        assert "task2_timeout" in results
        assert "task2_acquired" not in results

    async def test_manager_start_stop(self):
        """
        Teste: Manager deve iniciar e parar cleanup task corretamente.
        """
        # Arrange
        manager = InMemoryLockManager()

        # Act
        await manager.start()
        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()

        await manager.stop()

        # Assert
        assert manager._cleanup_task is None or manager._cleanup_task.done()
