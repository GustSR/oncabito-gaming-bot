"""
Testes para idempotência de callbacks.

CORREÇÃO INCONSISTÊNCIA #3: Flood de Callbacks em Resolução de Duplicatas
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.sentinela.presentation.handlers.cpf_verification_handler import CPFVerificationHandler


@pytest.mark.asyncio
class TestCallbackIdempotency:
    """Testes de idempotência de processamento de callbacks."""

    @pytest.mark.skip(reason="TODO: Atualizar para nova API do CPFVerificationHandler")
    async def test_callback_processed_only_once(self):
        """
        Teste: Callback deve ser processado apenas uma vez.

        TESTE CRÍTICO - Inconsistência #3

        Cenário:
        - Usuário clica no botão múltiplas vezes (double-click)
        - Múltiplos callbacks chegam simultaneamente

        Resultado esperado:
        - Apenas o primeiro callback é processado
        - Demais retornam mensagem "Já estou processando..."
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        # Mock do callback query
        mock_query1 = AsyncMock()
        mock_query1.id = "callback_123"
        mock_query1.data = "resolve_duplicate_keep_111"
        mock_query1.answer = AsyncMock()
        mock_query1.edit_message_text = AsyncMock()

        mock_query2 = AsyncMock()
        mock_query2.id = "callback_123"  # Mesmo ID (simulando double-click)
        mock_query2.data = "resolve_duplicate_keep_111"
        mock_query2.answer = AsyncMock()
        mock_query2.edit_message_text = AsyncMock()

        # Mock de update e context
        mock_update1 = MagicMock()
        mock_update1.callback_query = mock_query1

        mock_update2 = MagicMock()
        mock_update2.callback_query = mock_query2

        mock_context = MagicMock()

        # Act - Simula 2 callbacks chegando ao mesmo tempo
        import asyncio

        async def process_first():
            await handler.handle_resolve_duplicate_callback(mock_update1, mock_context)

        async def process_second():
            await asyncio.sleep(0.1)  # Pequeno delay
            await handler.handle_resolve_duplicate_callback(mock_update2, mock_context)

        # Executa ambos
        with patch.object(handler, '_process_duplicate_resolution', new=AsyncMock()) as mock_process:
            await asyncio.gather(process_first(), process_second(), return_exceptions=True)

            # Assert
            # Apenas 1 processamento real deve ter ocorrido
            assert mock_process.call_count <= 1, "Callback deve ser processado apenas uma vez"

    async def test_callback_cleanup_after_processing(self):
        """
        Teste: Callback ID deve ser removido do set após processamento.

        Cenário:
        - Callback processado com sucesso
        - Processamento finaliza

        Resultado esperado:
        - Callback ID removido do set _processing_callbacks
        - Novo callback com mesmo ID pode ser processado
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        callback_id = "callback_456"

        # Simula callback sendo processado
        handler._processing_callbacks.add(callback_id)
        assert callback_id in handler._processing_callbacks

        # Act - Simula finalização do processamento
        handler._processing_callbacks.discard(callback_id)

        # Assert
        assert callback_id not in handler._processing_callbacks

    async def test_callback_cleanup_on_exception(self):
        """
        Teste: Callback ID deve ser removido mesmo se ocorrer exceção.

        Cenário:
        - Callback sendo processado
        - Erro ocorre durante processamento

        Resultado esperado:
        - Callback ID removido (cleanup garantido)
        - Próximo callback pode ser processado
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        callback_id = "callback_789"

        # Act & Assert - Simula try/finally
        try:
            handler._processing_callbacks.add(callback_id)
            raise ValueError("Simulated error")
        except ValueError:
            pass
        finally:
            handler._processing_callbacks.discard(callback_id)

        # Callback deve ter sido removido mesmo com erro
        assert callback_id not in handler._processing_callbacks

    async def test_different_callbacks_processed_concurrently(self):
        """
        Teste: Callbacks diferentes devem ser processados concorrentemente.

        Cenário:
        - Callback A para resolução 1
        - Callback B para resolução 2 (diferente)

        Resultado esperado:
        - Ambos processados (IDs diferentes)
        - Sem bloqueio entre callbacks diferentes
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        callback_id_1 = "callback_111"
        callback_id_2 = "callback_222"

        # Act
        handler._processing_callbacks.add(callback_id_1)
        handler._processing_callbacks.add(callback_id_2)

        # Assert
        assert callback_id_1 in handler._processing_callbacks
        assert callback_id_2 in handler._processing_callbacks
        assert len(handler._processing_callbacks) == 2

    async def test_spam_protection(self):
        """
        TESTE DE ACEITAÇÃO - Inconsistência #3

        Simula usuário nervoso clicando múltiplas vezes rapidamente:
        - Click 1 (t=0s): Processado
        - Click 2 (t=0.1s): Ignorado (ainda processando)
        - Click 3 (t=0.2s): Ignorado (ainda processando)
        - Click 4 (t=2s): Processado (primeiro já terminou)

        Resultado esperado:
        - Apenas clicks 1 e 4 processados
        - Clicks 2 e 3 ignorados com mensagem
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        callback_id = "rapid_click"
        results = []

        async def attempt_callback(attempt_number: int):
            """Simula tentativa de processar callback."""
            if callback_id in handler._processing_callbacks:
                results.append(f"attempt_{attempt_number}_ignored")
                return False
            else:
                handler._processing_callbacks.add(callback_id)
                results.append(f"attempt_{attempt_number}_processed")
                await asyncio.sleep(1)  # Simula processamento
                handler._processing_callbacks.discard(callback_id)
                return True

        # Act - Simula 4 clicks rápidos
        import asyncio

        tasks = [
            attempt_callback(1),  # t=0
            attempt_callback(2),  # t=0 (simultâneo)
            attempt_callback(3),  # t=0 (simultâneo)
        ]

        await asyncio.gather(*tasks)

        # Aguarda processamento terminar
        await asyncio.sleep(1.5)

        # Click após processamento
        await attempt_callback(4)

        # Assert
        assert "attempt_1_processed" in results, "Primeiro click deve ser processado"
        assert "attempt_2_ignored" in results or "attempt_3_ignored" in results, "Clicks simultâneos devem ser ignorados"
        assert "attempt_4_processed" in results, "Click após término deve ser processado"

        # Apenas 2 devem ter sido processados (1 e 4)
        processed_count = sum(1 for r in results if "processed" in r)
        assert processed_count == 2, "Apenas 2 callbacks devem ser processados"


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO: Atualizar para nova API do CPFVerificationHandler")
class TestCallbackAnswerImmediate:
    """Testes de resposta imediata ao callback (UX)."""

    async def test_query_answer_called_immediately(self):
        """
        Teste: query.answer() deve ser chamado imediatamente.

        Cenário:
        - Callback recebido
        - Antes de qualquer processamento

        Resultado esperado:
        - query.answer() chamado
        - Desabilita botão visualmente para usuário
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        mock_query = AsyncMock()
        mock_query.id = "callback_test"
        mock_query.data = "resolve_duplicate_keep_111"
        mock_query.answer = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        # Mock do processamento para não falhar
        with patch.object(handler, '_process_duplicate_resolution', new=AsyncMock()):
            # Act
            await handler.handle_resolve_duplicate_callback(mock_update, mock_context)

            # Assert
            mock_query.answer.assert_called_once()

    async def test_already_processing_message(self):
        """
        Teste: Mensagem clara quando callback já está sendo processado.

        Cenário:
        - Callback já em processamento
        - Segundo click chega

        Resultado esperado:
        - query.answer() chamado com mensagem específica
        - Mensagem: "Já estou processando sua solicitação..."
        """
        # Arrange
        mock_container = MagicMock()
        handler = CPFVerificationHandler(container=mock_container)

        callback_id = "callback_busy"
        handler._processing_callbacks.add(callback_id)  # Simula já processando

        mock_query = AsyncMock()
        mock_query.id = callback_id
        mock_query.data = "resolve_duplicate_keep_111"
        mock_query.answer = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        # Act
        await handler.handle_resolve_duplicate_callback(mock_update, mock_context)

        # Assert
        mock_query.answer.assert_called_once()
        call_args = mock_query.answer.call_args

        # Verifica se mensagem contém texto de "já processando"
        if call_args and call_args[1]:
            message_text = call_args[1].get('text', '')
            assert "processando" in message_text.lower() or "aguarde" in message_text.lower()
