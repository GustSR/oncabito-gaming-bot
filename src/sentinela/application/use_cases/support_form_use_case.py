"""
Use Case para gerenciar formulário conversacional de suporte.

Este Use Case substitui a classe SupportFormManager do código antigo,
implementando a mesma funcionalidade usando a nova arquitetura.
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum

from ..base import UseCase
from ...domain.repositories.user_repository import UserRepository
from ...domain.repositories.support_conversation_repository import SupportConversationRepository
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.entities.support_conversation import SupportConversation, ConversationBusinessRuleError
from ...domain.entities.ticket import Ticket, TicketAttachment
from ...domain.value_objects.identifiers import UserId
from ...domain.value_objects.ticket_category import TicketCategory, GameTitle, ProblemTiming

logger = logging.getLogger(__name__)


class SupportFormStep(Enum):
    """Passos do formulário de suporte."""
    CATEGORY_SELECTION = "category_selection"
    GAME_SELECTION = "game_selection"
    TIMING_SELECTION = "timing_selection"
    DESCRIPTION_INPUT = "description_input"
    ATTACHMENTS_OPTIONAL = "attachments_optional"
    CONFIRMATION = "confirmation"


class SupportFormResult:
    """Resultado de operação do formulário de suporte."""

    def __init__(
        self,
        success: bool,
        message: str,
        conversation: Optional[SupportConversation] = None,
        ticket: Optional[Ticket] = None,
        next_step: Optional[SupportFormStep] = None,
        keyboard_options: Optional[List[Dict[str, str]]] = None
    ):
        self.success = success
        self.message = message
        self.conversation = conversation
        self.ticket = ticket
        self.next_step = next_step
        self.keyboard_options = keyboard_options or []


class SupportFormUseCase(UseCase):
    """
    Use Case para gerenciar formulário conversacional de suporte.

    Coordena todas as operações relacionadas ao formulário de suporte:
    - Gerenciamento de estado da conversa
    - Validação de entradas
    - Criação de tickets
    - Interface com repositórios
    """

    def __init__(
        self,
        user_repository: UserRepository,
        conversation_repository: SupportConversationRepository,
        ticket_repository: TicketRepository
    ):
        self._user_repository = user_repository
        self._conversation_repository = conversation_repository
        self._ticket_repository = ticket_repository

    async def start_conversation(self, user_id: int, username: str) -> SupportFormResult:
        """
        Inicia nova conversa de suporte.

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            user_id_vo = UserId(user_id)

            # Busca usuário
            user = await self._user_repository.find_by_id(user_id_vo)
            if not user:
                return SupportFormResult(
                    success=False,
                    message="❌ Usuário não encontrado. Use /start para se registrar."
                )

            # Verifica se pode criar tickets
            if not user.can_create_ticket():
                return SupportFormResult(
                    success=False,
                    message="❌ Sua conta não está ativa para criar tickets."
                )

            # Verifica conversa ativa existente
            existing = await self._conversation_repository.find_active_by_user(user_id_vo)
            if existing:
                return SupportFormResult(
                    success=False,
                    message=f"💬 Você já tem um formulário em andamento. Progresso: {existing.get_progress_percentage()}%",
                    conversation=existing
                )

            # Cria nova conversa
            conversation = SupportConversation(None, user)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_category_selection_message(),
                conversation=conversation,
                next_step=SupportFormStep.CATEGORY_SELECTION,
                keyboard_options=self._get_category_options()
            )

        except Exception as e:
            logger.error(f"Erro ao iniciar conversa de suporte: {e}")
            return SupportFormResult(
                success=False,
                message="❌ Erro interno. Tente novamente."
            )

    async def process_category_selection(self, user_id: int, category_key: str) -> SupportFormResult:
        """
        Processa seleção de categoria.

        Args:
            user_id: ID do usuário
            category_key: Chave da categoria selecionada

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            # Valida e define categoria
            conversation.select_category(category_key)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_game_selection_message(),
                conversation=conversation,
                next_step=SupportFormStep.GAME_SELECTION,
                keyboard_options=self._get_game_options()
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao processar categoria: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def process_game_selection(self, user_id: int, game_key: str, custom_name: str = "") -> SupportFormResult:
        """
        Processa seleção de jogo.

        Args:
            user_id: ID do usuário
            game_key: Chave do jogo selecionado
            custom_name: Nome customizado (para "outro jogo")

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            conversation.select_game(game_key, custom_name)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_timing_selection_message(),
                conversation=conversation,
                next_step=SupportFormStep.TIMING_SELECTION,
                keyboard_options=self._get_timing_options()
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao processar jogo: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def process_timing_selection(self, user_id: int, timing_key: str) -> SupportFormResult:
        """
        Processa seleção de timing.

        Args:
            user_id: ID do usuário
            timing_key: Chave do timing selecionado

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            conversation.select_timing(timing_key)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_description_input_message(),
                conversation=conversation,
                next_step=SupportFormStep.DESCRIPTION_INPUT
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao processar timing: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def process_description_input(self, user_id: int, description: str) -> SupportFormResult:
        """
        Processa entrada da descrição.

        Args:
            user_id: ID do usuário
            description: Descrição do problema

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            conversation.set_description(description)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_attachments_message(),
                conversation=conversation,
                next_step=SupportFormStep.ATTACHMENTS_OPTIONAL,
                keyboard_options=self._get_attachment_options()
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao processar descrição: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def process_attachment(self, user_id: int, attachment: TicketAttachment) -> SupportFormResult:
        """
        Processa anexo de arquivo.

        Args:
            user_id: ID do usuário
            attachment: Anexo do ticket

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            conversation.add_attachment(attachment)
            await self._conversation_repository.save(conversation)

            attachments_count = len(conversation.form_data.get("attachments", []))

            return SupportFormResult(
                success=True,
                message=f"✅ Anexo {attachments_count}/3 adicionado com sucesso!\n\n" +
                        self._format_attachments_message(),
                conversation=conversation,
                next_step=SupportFormStep.ATTACHMENTS_OPTIONAL,
                keyboard_options=self._get_attachment_options()
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao processar anexo: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def proceed_to_confirmation(self, user_id: int) -> SupportFormResult:
        """
        Avança para confirmação.

        Args:
            user_id: ID do usuário

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            conversation.proceed_to_confirmation()
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message=self._format_confirmation_message(conversation),
                conversation=conversation,
                next_step=SupportFormStep.CONFIRMATION,
                keyboard_options=self._get_confirmation_options()
            )

        except Exception as e:
            logger.error(f"Erro ao avançar para confirmação: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    async def confirm_and_create_ticket(self, user_id: int) -> SupportFormResult:
        """
        Confirma e cria ticket final.

        Args:
            user_id: ID do usuário

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return self._no_active_conversation_result()

            # Cria ticket a partir da conversa
            ticket = conversation.confirm_and_create_ticket()

            # Salva ticket e conversa atualizada
            await self._ticket_repository.save(ticket)
            await self._conversation_repository.save(conversation)

            logger.info(f"Ticket {ticket.id} criado com sucesso para usuário {user_id}")

            return SupportFormResult(
                success=True,
                message=self._format_ticket_created_message(ticket),
                conversation=conversation,
                ticket=ticket
            )

        except ConversationBusinessRuleError as e:
            return SupportFormResult(success=False, message=f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            return SupportFormResult(success=False, message="❌ Erro ao criar ticket.")

    async def cancel_conversation(self, user_id: int, reason: str = "Usuário cancelou") -> SupportFormResult:
        """
        Cancela conversa ativa.

        Args:
            user_id: ID do usuário
            reason: Motivo do cancelamento

        Returns:
            SupportFormResult: Resultado da operação
        """
        try:
            conversation = await self._get_active_conversation(user_id)
            if not conversation:
                return SupportFormResult(
                    success=False,
                    message="❌ Nenhuma conversa de suporte ativa encontrada."
                )

            conversation.cancel(reason)
            await self._conversation_repository.save(conversation)

            return SupportFormResult(
                success=True,
                message="✅ Formulário de suporte cancelado. Você pode iniciar um novo a qualquer momento com /suporte."
            )

        except Exception as e:
            logger.error(f"Erro ao cancelar conversa: {e}")
            return SupportFormResult(success=False, message="❌ Erro interno.")

    # Helper methods

    async def _get_active_conversation(self, user_id: int) -> Optional[SupportConversation]:
        """Busca conversa ativa do usuário."""
        user_id_vo = UserId(user_id)
        return await self._conversation_repository.find_active_by_user(user_id_vo)

    def _no_active_conversation_result(self) -> SupportFormResult:
        """Resultado para quando não há conversa ativa."""
        return SupportFormResult(
            success=False,
            message="❌ Nenhuma conversa de suporte ativa. Use /suporte para iniciar."
        )

    # Message formatting methods

    def _format_category_selection_message(self) -> str:
        """Formata mensagem de seleção de categoria."""
        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**1/6 - Qual é a categoria do seu problema?**\n\n"
            "Escolha a opção que melhor descreve seu problema:"
        )

    def _format_game_selection_message(self) -> str:
        """Formata mensagem de seleção de jogo."""
        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**2/6 - Qual jogo está sendo afetado?**\n\n"
            "Selecione o jogo com problema:"
        )

    def _format_timing_selection_message(self) -> str:
        """Formata mensagem de seleção de timing."""
        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**3/6 - Quando o problema começou?**\n\n"
            "Isso nos ajuda a identificar a causa:"
        )

    def _format_description_input_message(self) -> str:
        """Formata mensagem de entrada de descrição."""
        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**4/6 - Descreva detalhadamente o problema**\n\n"
            "📝 **Digite sua mensagem explicando:**\n"
            "• O que exatamente está acontecendo?\n"
            "• Quais sintomas você percebe?\n"
            "• Já tentou alguma solução?\n\n"
            "💡 **Dica:** Quanto mais detalhes, mais rápido poderemos ajudar!"
        )

    def _format_attachments_message(self) -> str:
        """Formata mensagem de anexos."""
        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**5/6 - Anexos (Opcional)**\n\n"
            "📎 **Você pode enviar até 3 imagens:**\n"
            "• Screenshots do problema\n"
            "• Fotos da tela\n"
            "• Prints de erro\n\n"
            "Isso pode ajudar muito no diagnóstico!"
        )

    def _format_confirmation_message(self, conversation: SupportConversation) -> str:
        """Formata mensagem de confirmação."""
        form_data = conversation.form_data

        # Busca display names dos value objects
        try:
            category = TicketCategory.from_string(form_data["category"])
            game = GameTitle.from_string(form_data["game"], form_data.get("custom_game_name", ""))
            timing = ProblemTiming.from_string(form_data["timing"])
        except Exception:
            # Fallback caso value objects falhem
            category = type('obj', (object,), {'display_name': form_data["category"]})()
            game = type('obj', (object,), {'display_name': form_data["game"]})()
            timing = type('obj', (object,), {'display_name': form_data["timing"]})()

        attachments_count = len(form_data.get("attachments", []))

        return (
            "🎮 **SUPORTE GAMER ONCABO**\n\n"
            "**6/6 - Confirmação dos dados**\n\n"
            "📋 **RESUMO DO SEU CHAMADO:**\n\n"
            f"🔸 **Categoria:** {category.display_name}\n"
            f"🔸 **Jogo:** {game.display_name}\n"
            f"🔸 **Quando começou:** {timing.display_name}\n"
            f"🔸 **Anexos:** {attachments_count} arquivo(s)\n\n"
            f"📝 **Descrição:**\n{form_data['description'][:200]}{'...' if len(form_data['description']) > 200 else ''}\n\n"
            "✅ **Confirma a criação do chamado?**"
        )

    def _format_ticket_created_message(self, ticket: Ticket) -> str:
        """Formata mensagem de ticket criado."""
        protocol = ticket.get_display_protocol()

        return (
            "🎉 **CHAMADO CRIADO COM SUCESSO!**\n\n"
            f"📋 **Protocolo:** `{protocol}`\n"
            f"📅 **Criado em:** {ticket.created_at.strftime('%d/%m/%Y às %H:%M')}\n"
            f"📊 **Status:** {ticket.status.value.title()}\n\n"
            "✅ **Seu chamado foi registrado!**\n\n"
            "📞 **Próximos passos:**\n"
            "• Nossa equipe irá analisar seu problema\n"
            "• Você receberá atualizações aqui no Telegram\n"
            "• Tempo de resposta: até 24h úteis\n\n"
            f"🔍 **Para acompanhar:** Use o protocolo `{protocol}`"
        )

    # Keyboard options methods

    def _get_category_options(self) -> List[Dict[str, str]]:
        """Retorna opções de categoria para teclado."""
        categories = TicketCategory.get_all_categories()
        return [
            {"text": category.display_name, "callback_data": f"category_{key}"}
            for key, category in categories.items()
        ]

    def _get_game_options(self) -> List[Dict[str, str]]:
        """Retorna opções de jogos para teclado."""
        games = GameTitle.get_popular_games()
        return [
            {"text": game.display_name, "callback_data": f"game_{key}"}
            for key, game in games.items()
        ]

    def _get_timing_options(self) -> List[Dict[str, str]]:
        """Retorna opções de timing para teclado."""
        timings = ProblemTiming.get_all_timings()
        return [
            {"text": timing.display_name, "callback_data": f"timing_{key}"}
            for key, timing in timings.items()
        ]

    def _get_attachment_options(self) -> List[Dict[str, str]]:
        """Retorna opções de anexos para teclado."""
        return [
            {"text": "📎 Enviar anexo", "callback_data": "attachment_send"},
            {"text": "⏭️ Prosseguir", "callback_data": "attachment_skip"}
        ]

    def _get_confirmation_options(self) -> List[Dict[str, str]]:
        """Retorna opções de confirmação para teclado."""
        return [
            {"text": "✅ Confirmar e criar chamado", "callback_data": "confirm_create"},
            {"text": "❌ Cancelar", "callback_data": "confirm_cancel"}
        ]