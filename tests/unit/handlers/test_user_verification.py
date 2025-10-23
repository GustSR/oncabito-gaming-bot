"""
Testes críticos para verificação de usuário.

Testa o comportamento corrigido na TASK-002: usuários com CPF COMPLETED
mas status INACTIVE não devem ter acesso às funcionalidades.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Atualizar para nova API do TelegramBotHandler")
class TestUserVerification:
    """Testes de verificação de usuário."""

    async def test_active_user_should_have_access(
        self,
        mock_container,
        mock_user_repository,
        mock_user_entity
    ):
        """
        Teste: Usuário ACTIVE deve ter acesso.

        Cenário:
        - Usuário tem status ACTIVE
        - CPF pode ou não estar COMPLETED

        Resultado esperado:
        - _check_user_verified() retorna True
        - Usuário pode acessar funcionalidades
        """
        # Arrange
        from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler

        mock_user_repository.find_by_telegram_id.return_value = mock_user_entity
        mock_container.get.return_value = mock_user_repository

        handler = TelegramBotHandler(container=mock_container)
        await handler._ensure_initialized()

        # Act
        is_verified = await handler._check_user_verified(123456)

        # Assert
        assert is_verified is True, "Usuário ACTIVE deve ser considerado verificado"
        mock_user_repository.find_by_telegram_id.assert_called_once_with(123456)


    async def test_inactive_user_should_not_have_access(
        self,
        mock_container,
        mock_user_repository,
        mock_inactive_user_entity
    ):
        """
        Teste: Usuário INACTIVE não deve ter acesso.

        Cenário:
        - Usuário tem status INACTIVE
        - CPF pode estar COMPLETED (não importa)

        Resultado esperado:
        - _check_user_verified() retorna False
        - Usuário NÃO pode acessar funcionalidades
        """
        # Arrange
        from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler

        mock_user_repository.find_by_telegram_id.return_value = mock_inactive_user_entity
        mock_container.get.return_value = mock_user_repository

        handler = TelegramBotHandler(container=mock_container)
        await handler._ensure_initialized()

        # Act
        is_verified = await handler._check_user_verified(789012)

        # Assert
        assert is_verified is False, "Usuário INACTIVE não deve ser considerado verificado"
        mock_user_repository.find_by_telegram_id.assert_called_once_with(789012)


    async def test_bug_task_002_cpf_completed_but_user_inactive(
        self,
        mock_container,
        mock_user_repository,
        mock_cpf_repository,
        mock_inactive_user_entity
    ):
        """
        TESTE CRÍTICO: Reproduz bug identificado na TASK-002.

        Cenário:
        - Usuário tem CPF verificado (COMPLETED) ✅
        - Mas status do usuário é INACTIVE ❌ (plano cancelado)

        Comportamento esperado (CORRETO):
        - _check_user_verified() deve retornar False
        - Usuário NÃO deve ter acesso

        Comportamento anterior (BUG - já corrigido):
        - _get_verification_status_message()["is_verified"] retornava True
        - Usuário passava pela validação indevidamente

        Este teste garante que o bug não volte!
        """
        # Arrange
        from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler
        from src.sentinela.domain.entities.cpf_verification import VerificationStatus

        # Simula CPF COMPLETED
        mock_cpf_verification = MagicMock()
        mock_cpf_verification.status = VerificationStatus.COMPLETED
        mock_cpf_repository.find_by_user_id.return_value = [mock_cpf_verification]

        # Mas usuário está INACTIVE
        mock_user_repository.find_by_telegram_id.return_value = mock_inactive_user_entity

        def container_get(key):
            if key == "user_repository":
                return mock_user_repository
            elif key == "cpf_verification_repository":
                return mock_cpf_repository
            return None

        mock_container.get.side_effect = container_get

        handler = TelegramBotHandler(container=mock_container)
        await handler._ensure_initialized()

        # Act - Usa a função CORRETA de verificação
        is_verified = await handler._check_user_verified(789012)

        # Assert
        assert is_verified is False, (
            "BUG TASK-002: Usuário com CPF COMPLETED mas status INACTIVE "
            "não deve ser considerado verificado! "
            "A função _check_user_verified() deve verificar o status do User, "
            "não apenas o status da CPFVerification."
        )

        # Verifica que consultou o repositório correto (user_repository)
        mock_user_repository.find_by_telegram_id.assert_called_once_with(789012)


    async def test_user_not_found_should_return_false(
        self,
        mock_container,
        mock_user_repository
    ):
        """
        Teste: Usuário não encontrado deve retornar False.

        Cenário:
        - Usuário não existe no banco

        Resultado esperado:
        - _check_user_verified() retorna False
        """
        # Arrange
        from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler

        mock_user_repository.find_by_telegram_id.return_value = None
        mock_container.get.return_value = mock_user_repository

        handler = TelegramBotHandler(container=mock_container)
        await handler._ensure_initialized()

        # Act
        is_verified = await handler._check_user_verified(999999)

        # Assert
        assert is_verified is False, "Usuário não encontrado não deve ser considerado verificado"
        mock_user_repository.find_by_telegram_id.assert_called_once_with(999999)


    async def test_repository_error_should_return_false(
        self,
        mock_container,
        mock_user_repository
    ):
        """
        Teste: Erro no repositório deve retornar False (fail-safe).

        Cenário:
        - Erro ao consultar banco de dados

        Resultado esperado:
        - _check_user_verified() retorna False (seguro)
        - Não quebra o bot
        """
        # Arrange
        from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler

        mock_user_repository.find_by_telegram_id.side_effect = Exception("Database error")
        mock_container.get.return_value = mock_user_repository

        handler = TelegramBotHandler(container=mock_container)
        await handler._ensure_initialized()

        # Act
        is_verified = await handler._check_user_verified(123456)

        # Assert
        assert is_verified is False, "Erro no repositório deve retornar False (fail-safe)"
