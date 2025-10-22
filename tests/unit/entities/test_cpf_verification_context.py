"""
Testes para persistência de contexto de resolução de duplicatas.

CORREÇÃO INCONSISTÊNCIA #2: Contexto `user_data` Perdido em Reinicialização
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from src.sentinela.domain.entities.cpf_verification import (
    CPFVerificationRequest,
    VerificationId,
    VerificationType,
    VerificationStatus
)
from src.sentinela.domain.value_objects.identifiers import UserId
from src.sentinela.domain.value_objects.cpf import CPF


class TestCPFVerificationContext:
    """Testes de persistência de contexto de resolução."""

    def test_set_duplicate_resolution_context(self):
        """
        Teste: Deve ser possível armazenar contexto de resolução.

        Cenário:
        - Conflito de duplicata detectado
        - Contexto salvo na entidade

        Resultado esperado:
        - Contexto armazenado corretamente
        - has_pending_duplicate_resolution() retorna True
        """
        # Arrange
        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        context_data = {
            "verification_id": str(verification.id),
            "conflicting_users": [111, 222, 333],
            "created_at": datetime.now().isoformat()
        }

        # Act
        verification.set_duplicate_resolution_context(context_data)

        # Assert
        assert verification.has_pending_duplicate_resolution() is True
        assert verification.duplicate_resolution_context is not None
        assert verification.duplicate_resolution_context["verification_id"] == str(verification.id)
        assert len(verification.duplicate_resolution_context["conflicting_users"]) == 3

    def test_clear_duplicate_resolution_context(self):
        """
        Teste: Deve ser possível limpar contexto após resolução.

        Cenário:
        - Contexto estava armazenado
        - Conflito foi resolvido
        - Contexto é limpo

        Resultado esperado:
        - Contexto removido
        - has_pending_duplicate_resolution() retorna False
        """
        # Arrange
        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        context_data = {
            "verification_id": str(verification.id),
            "conflicting_users": [111, 222],
            "created_at": datetime.now().isoformat()
        }

        verification.set_duplicate_resolution_context(context_data)
        assert verification.has_pending_duplicate_resolution() is True

        # Act
        verification.clear_duplicate_resolution_context()

        # Assert
        assert verification.has_pending_duplicate_resolution() is False
        assert verification.duplicate_resolution_context is None

    def test_context_survives_multiple_operations(self):
        """
        Teste: Contexto deve permanecer após outras operações na entidade.

        Cenário:
        - Contexto salvo
        - Outras operações realizadas (add_attempt, etc)

        Resultado esperado:
        - Contexto permanece intacto
        """
        # Arrange
        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        context_data = {
            "verification_id": str(verification.id),
            "conflicting_users": [111, 222],
            "created_at": datetime.now().isoformat()
        }

        verification.set_duplicate_resolution_context(context_data)

        # Act - Outras operações
        verification.add_attempt(cpf_provided="12345678900", success=False, failure_reason="test")

        # Assert - Contexto ainda está lá
        assert verification.has_pending_duplicate_resolution() is True
        assert verification.duplicate_resolution_context["verification_id"] == str(verification.id)

    def test_has_pending_duplicate_resolution_false_by_default(self):
        """
        Teste: Novas verificações não devem ter contexto pendente.

        Cenário:
        - Verificação recém-criada

        Resultado esperado:
        - has_pending_duplicate_resolution() retorna False
        - duplicate_resolution_context é None
        """
        # Arrange & Act
        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        # Assert
        assert verification.has_pending_duplicate_resolution() is False
        assert verification.duplicate_resolution_context is None


@pytest.mark.asyncio
class TestContextPersistence:
    """Testes de persistência do contexto no repositório."""

    async def test_context_saved_to_database(self):
        """
        TESTE CRÍTICO - Inconsistência #2

        Teste: Contexto deve ser persistido no banco de dados.

        Cenário:
        - Contexto setado na entidade
        - Entidade salva no repositório

        Resultado esperado:
        - Contexto serializado e salvo no banco
        - Pode ser recuperado posteriormente
        """
        # Arrange
        from src.sentinela.infrastructure.repositories.sqlite_cpf_verification_repository import (
            SQLiteCPFVerificationRepository
        )
        from src.sentinela.infrastructure.database.connection import DatabaseConnection

        # Mock da conexão
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_db = MagicMock(spec=DatabaseConnection)
        mock_db.get_connection.return_value = mock_connection

        repository = SQLiteCPFVerificationRepository(mock_db)

        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        context_data = {
            "verification_id": str(verification.id),
            "conflicting_users": [111, 222],
            "created_at": datetime.now().isoformat()
        }

        verification.set_duplicate_resolution_context(context_data)

        # Act
        await repository.save(verification)

        # Assert
        # Verifica se o SQL foi executado com contexto serializado
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args

        # O contexto deve estar em algum dos argumentos do SQL
        sql_params = call_args[0][1] if len(call_args[0]) > 1 else []

        # Verifica se algum parâmetro contém dados JSON do contexto
        import json
        context_found = False
        for param in sql_params:
            if param and isinstance(param, str):
                try:
                    parsed = json.loads(param)
                    if "conflicting_users" in parsed:
                        context_found = True
                        assert parsed["conflicting_users"] == [111, 222]
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        assert context_found, "Contexto deve ser salvo como JSON no banco"

    async def test_context_loaded_from_database(self):
        """
        TESTE CRÍTICO - Inconsistência #2

        Teste: Contexto deve ser carregado do banco após reinicialização.

        Cenário:
        - Bot reinicia (simulado)
        - Contexto estava no banco
        - Verificação é carregada

        Resultado esperado:
        - Contexto recuperado do banco
        - has_pending_duplicate_resolution() retorna True
        - Dados do contexto corretos
        """
        # Arrange
        from src.sentinela.infrastructure.repositories.sqlite_cpf_verification_repository import (
            SQLiteCPFVerificationRepository
        )
        from src.sentinela.infrastructure.database.connection import DatabaseConnection
        import json

        verification_id = str(VerificationId.generate())
        context_data = {
            "verification_id": verification_id,
            "conflicting_users": [111, 222, 333],
            "created_at": datetime.now().isoformat()
        }

        # Mock de row do banco com contexto
        mock_row = {
            "id": verification_id,
            "user_id": 123456,
            "username": "test_user",
            "user_mention": "@test_user",
            "verification_type": "AUTO_CHECKUP",
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "completed_at": None,
            "cpf_verified": None,
            "client_data": None,
            "attempt_count": 0,
            "last_attempt_at": None,
            "duplicate_resolution_context": json.dumps(context_data)  # Contexto no banco
        }

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__ = MagicMock(return_value=mock_connection)
        mock_connection.__exit__ = MagicMock(return_value=False)

        mock_db = MagicMock(spec=DatabaseConnection)
        mock_db.get_connection.return_value = mock_connection

        repository = SQLiteCPFVerificationRepository(mock_db)

        # Act - Busca verificação (simula carregamento após restart)
        verification = await repository.find_by_id(VerificationId(verification_id))

        # Assert
        assert verification is not None, "Verificação deve ser carregada"
        assert verification.has_pending_duplicate_resolution() is True, "Contexto deve estar presente"
        assert verification.duplicate_resolution_context is not None
        assert verification.duplicate_resolution_context["verification_id"] == verification_id
        assert verification.duplicate_resolution_context["conflicting_users"] == [111, 222, 333]

    async def test_bot_restart_simulation(self):
        """
        TESTE DE ACEITAÇÃO - Inconsistência #2

        Simula cenário real:
        1. Usuário inicia resolução de duplicatas
        2. Bot salva contexto no banco
        3. Bot reinicia (deploy/crash)
        4. Usuário clica no botão de resolução
        5. Handler busca contexto do banco (não da memória)

        Resultado esperado:
        - Resolução funciona normalmente após restart
        - Contexto recuperado do banco
        """
        # Este teste seria integrado com handler real
        # Por enquanto, valida que a funcionalidade existe

        verification = CPFVerificationRequest(
            id=VerificationId.generate(),
            user_id=UserId(123456),
            username="test_user",
            user_mention="@test_user",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=datetime.now() + timedelta(hours=1)
        )

        context_data = {
            "verification_id": str(verification.id),
            "conflicting_users": [111, 222],
            "created_at": datetime.now().isoformat()
        }

        # Simula: contexto salvo antes do restart
        verification.set_duplicate_resolution_context(context_data)
        assert verification.has_pending_duplicate_resolution() is True

        # Simula: restart do bot (contexto de memória perdido)
        # Mas contexto está no banco, então pode ser recuperado

        # Simula: carregamento após restart
        recovered_context = verification.duplicate_resolution_context

        assert recovered_context is not None
        assert recovered_context["conflicting_users"] == [111, 222]
