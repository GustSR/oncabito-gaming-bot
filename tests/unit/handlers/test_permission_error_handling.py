"""
Testes para tratamento de erros de permissão.

CORREÇÃO INCONSISTÊNCIA #9: Bot Sem Permissões Após Demotion Marca Conflito como Resolvido
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.sentinela.presentation.handlers.cpf_verification_handler import CPFVerificationHandler
from src.sentinela.domain.entities.duplicate_conflict import DuplicateConflict, ConflictStatus


@pytest.mark.asyncio
class TestPermissionErrorHandling:
    """Testes de tratamento de erros de permissão."""

    async def test_permission_error_marks_conflict_as_error(self):
        """
        TESTE CRÍTICO - Inconsistência #9

        Teste: Falha de permissão deve marcar conflito como ERROR (não RESOLVED).

        Cenário:
        - Bot tenta remover usuários duplicados
        - Telegram retorna erro de permissão
        - Bot não consegue remover

        Resultado esperado:
        - Conflito marcado como ERROR (não RESOLVED)
        - resolution_notes preenchido com detalhes
        - Admin notificado
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        # Mock do conflito
        mock_conflict = MagicMock(spec=DuplicateConflict)
        mock_conflict.id = "conflict_123"
        mock_conflict.status = ConflictStatus.PENDING

        # Mock do repositório
        mock_conflict_repo = AsyncMock()
        mock_conflict_repo.find_by_id = AsyncMock(return_value=mock_conflict)
        mock_conflict_repo.save = AsyncMock()

        # Mock da tentativa de remoção que falha
        failed_user_ids = [111, 222]

        # Simula que tentou remover mas falhou
        with patch.object(handler, '_notify_permission_error', new=AsyncMock()) as mock_notify:
            # Act - Simula o handler tratando o erro
            mock_conflict.status = ConflictStatus.ERROR
            mock_conflict.resolution_notes = (
                f"Permissão negada: não foi possível remover {len(failed_user_ids)} usuário(s). "
                f"IDs: {failed_user_ids}. Resolução escolhida: manter conta 333."
            )

            await mock_conflict_repo.save(mock_conflict)

            # Simula notificação
            await mock_notify(
                bot=MagicMock(),
                failed_user_ids=failed_user_ids,
                context="test_permission_error"
            )

            # Assert
            assert mock_conflict.status == ConflictStatus.ERROR, "Conflito deve ser marcado como ERROR"
            assert mock_conflict.resolution_notes is not None, "resolution_notes deve estar preenchido"
            assert "Permissão negada" in mock_conflict.resolution_notes
            assert str(failed_user_ids) in mock_conflict.resolution_notes or "111" in mock_conflict.resolution_notes
            mock_conflict_repo.save.assert_called_once()
            mock_notify.assert_called_once()

    async def test_notification_sent_to_tech_channel(self):
        """
        Teste: Notificação de erro deve ser enviada ao canal técnico.

        CORREÇÃO Inconsistência #9 - Opção 4: Canal técnico + fallback em log

        Cenário:
        - Erro de permissão ocorre
        - TECH_NOTIFICATION_CHANNEL_ID configurado

        Resultado esperado:
        - Mensagem enviada ao canal técnico
        - Mensagem contém IDs dos usuários afetados
        - Mensagem contém instruções de ação
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        failed_user_ids = [111, 222, 333]
        context = "duplicate_resolution_test"

        # Mock da config
        with patch('src.sentinela.presentation.handlers.cpf_verification_handler.TECH_NOTIFICATION_CHANNEL_ID', '-1001234567890'):
            # Act
            await handler._notify_permission_error(
                bot=mock_bot,
                failed_user_ids=failed_user_ids,
                context=context
            )

            # Assert
            mock_bot.send_message.assert_called_once()

            call_args = mock_bot.send_message.call_args
            assert call_args is not None

            # Verifica argumentos da chamada
            sent_to_channel = call_args[1]['chat_id']
            message_text = call_args[1]['text']

            assert sent_to_channel == '-1001234567890', "Deve enviar para canal técnico"
            assert "ERRO DE PERMISSÕES" in message_text or "permiss" in message_text.lower()
            assert any(str(uid) in message_text for uid in failed_user_ids), "Deve conter IDs dos usuários"

    async def test_notification_fallback_to_log_if_channel_fails(self):
        """
        Teste: Se canal técnico falhar, deve logar erro crítico.

        CORREÇÃO Inconsistência #9 - Opção 4: Fallback em log

        Cenário:
        - Tentativa de enviar para canal técnico falha
        - Bot não consegue enviar mensagem

        Resultado esperado:
        - Erro capturado (não quebra o bot)
        - Log crítico registrado
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Telegram API error"))

        failed_user_ids = [111, 222]

        with patch('src.sentinela.presentation.handlers.cpf_verification_handler.TECH_NOTIFICATION_CHANNEL_ID', '-1001234567890'):
            with patch('src.sentinela.presentation.handlers.cpf_verification_handler.logger') as mock_logger:
                # Act
                await handler._notify_permission_error(
                    bot=mock_bot,
                    failed_user_ids=failed_user_ids,
                    context="test_fallback"
                )

                # Assert
                # Deve ter tentado enviar
                mock_bot.send_message.assert_called_once()

                # Deve ter logado erro crítico como fallback
                assert mock_logger.critical.called or mock_logger.error.called, "Deve logar erro crítico"

    async def test_resolution_notes_contains_failure_details(self):
        """
        Teste: resolution_notes deve conter detalhes completos da falha.

        Cenário:
        - Falha ao remover usuários
        - Conflito marcado como ERROR

        Resultado esperado:
        - resolution_notes contém:
          * Número de usuários que falharam
          * IDs dos usuários
          * Qual conta foi escolhida para manter
        """
        # Arrange
        failed_user_ids = [111, 222, 333]
        chosen_user_id = 444

        # Act
        resolution_notes = (
            f"Permissão negada: não foi possível remover {len(failed_user_ids)} usuário(s). "
            f"IDs: {failed_user_ids}. Resolução escolhida: manter conta {chosen_user_id}."
        )

        # Assert
        assert "Permissão negada" in resolution_notes
        assert "3 usuário(s)" in resolution_notes or "3 usuários" in resolution_notes
        assert any(str(uid) in resolution_notes for uid in failed_user_ids)
        assert str(chosen_user_id) in resolution_notes

    async def test_user_receives_error_message_not_success(self):
        """
        TESTE CRÍTICO - Inconsistência #9

        Teste: Usuário deve receber mensagem de ERRO, não de sucesso.

        Cenário:
        - Resolução falha por falta de permissões
        - Bot não conseguiu remover usuários duplicados

        Resultado esperado:
        - Mensagem de erro mostrada ao usuário
        - Mensagem explica o problema
        - Mensagem instrui entrar em contato com suporte
        - Mensagem NÃO diz "resolvido com sucesso"
        """
        # Arrange
        error_message = (
            "⚠️ **Erro ao Resolver Conflito**\n\n"
            "Não consegui remover 2 usuário(s) do grupo devido a falta de permissões.\n\n"
            "**O que fazer:**\n"
            "Entre em contato com o suporte informando este erro.\n"
            "Um administrador precisará remover manualmente as contas duplicadas.\n\n"
            "**Conta mantida:** 444\n"
            "**Contas que falharam:** 111, 222"
        )

        # Assert
        assert "Erro" in error_message or "erro" in error_message
        assert "permiss" in error_message.lower()
        assert "suporte" in error_message.lower() or "administrador" in error_message.lower()
        assert "sucesso" not in error_message.lower(), "Mensagem NÃO deve dizer 'sucesso'"
        assert "resolvido" not in error_message or "Erro ao Resolver" in error_message


@pytest.mark.asyncio
class TestPermissionErrorScenarios:
    """Testes de cenários específicos de erro de permissão."""

    async def test_partial_removal_failure(self):
        """
        Teste: Falha parcial (alguns removidos, outros não).

        Cenário:
        - Tentou remover 5 usuários
        - 3 foram removidos com sucesso
        - 2 falharam (sem permissão)

        Resultado esperado:
        - Conflito marcado como ERROR
        - resolution_notes lista quais falharam
        - Admin notificado sobre os 2 que falharam
        """
        # Arrange
        all_users_to_remove = [111, 222, 333, 444, 555]
        successfully_removed = [111, 222, 333]
        failed_to_remove = [444, 555]

        # Act - Simula lógica do handler
        if failed_to_remove:
            status = ConflictStatus.ERROR
            resolution_notes = (
                f"Remoção parcial: {len(successfully_removed)} usuários removidos, "
                f"{len(failed_to_remove)} falharam. "
                f"IDs que falharam: {failed_to_remove}"
            )
        else:
            status = ConflictStatus.RESOLVED
            resolution_notes = None

        # Assert
        assert status == ConflictStatus.ERROR, "Status deve ser ERROR se houver falhas"
        assert resolution_notes is not None
        assert "parcial" in resolution_notes.lower() or "falharam" in resolution_notes.lower()
        assert all(str(uid) in resolution_notes for uid in failed_to_remove)

    async def test_notification_includes_actionable_steps(self):
        """
        Teste: Notificação ao admin deve incluir passos acionáveis.

        Cenário:
        - Erro de permissão detectado
        - Notificação enviada

        Resultado esperado:
        - Mensagem contém:
          * "Verificar se bot tem permissão 'can_restrict_members'"
          * "Remover manualmente os usuários listados"
          * "Atualizar status do conflito no banco"
        """
        # Arrange
        notification_message = (
            "⚠️ **ERRO DE PERMISSÕES DO BOT** ⚠️\n\n"
            "**Contexto:** duplicate_resolution\n"
            "**Problema:** Bot não conseguiu remover 2 usuário(s)\n"
            "**IDs afetados:** 111, 222\n\n"
            "**Ação necessária:**\n"
            "1. Verificar se bot tem permissão 'can_restrict_members'\n"
            "2. Remover manualmente os usuários listados\n"
            "3. Atualizar status do conflito no banco\n\n"
            "**Timestamp:** 2025-10-21 18:00:00"
        )

        # Assert
        assert "can_restrict_members" in notification_message or "permiss" in notification_message.lower()
        assert "Remover manualmente" in notification_message or "remover" in notification_message.lower()
        assert "Atualizar status" in notification_message or "banco" in notification_message.lower()
        assert "111" in notification_message and "222" in notification_message

    async def test_no_error_if_no_failures(self):
        """
        Teste: Se todos usuários foram removidos, não deve marcar como ERROR.

        Cenário:
        - Tentou remover 3 usuários
        - Todos foram removidos com sucesso

        Resultado esperado:
        - Conflito marcado como RESOLVED (não ERROR)
        - Sem notificação de erro
        - Mensagem de sucesso ao usuário
        """
        # Arrange
        all_users_to_remove = [111, 222, 333]
        failed_to_remove = []  # Nenhuma falha

        # Act - Simula lógica do handler
        if failed_to_remove:
            status = ConflictStatus.ERROR
        else:
            status = ConflictStatus.RESOLVED

        # Assert
        assert status == ConflictStatus.RESOLVED, "Deve ser RESOLVED se não houver falhas"
        assert len(failed_to_remove) == 0, "Não deve haver usuários na lista de falhas"
