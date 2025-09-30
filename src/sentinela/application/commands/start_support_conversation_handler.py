"""
Handler para comando de início de conversa de suporte.
"""

import logging
from typing import Optional

from .start_support_conversation_command import StartSupportConversationCommand
from ...domain.repositories.user_repository import UserRepository
from ...domain.repositories.support_conversation_repository import SupportConversationRepository
from ...domain.entities.support_conversation import SupportConversation
from ...domain.value_objects.identifiers import UserId
from ...domain.value_objects.base import ValidationError

logger = logging.getLogger(__name__)


class SupportConversationResult:
    """Resultado do início de conversa de suporte."""

    def __init__(
        self,
        success: bool,
        message: str,
        conversation: Optional[SupportConversation] = None,
        reason: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.conversation = conversation
        self.reason = reason


class StartSupportConversationHandler:
    """
    Handler para iniciar conversa de suporte.

    Implementa as regras de negócio para:
    1. Verificar se usuário pode criar tickets (anti-spam)
    2. Verificar se já tem conversa ativa
    3. Validar dados do usuário
    4. Iniciar nova conversa
    """

    def __init__(
        self,
        user_repository: UserRepository,
        conversation_repository: SupportConversationRepository
    ):
        self._user_repository = user_repository
        self._conversation_repository = conversation_repository

    async def handle(self, command: StartSupportConversationCommand) -> SupportConversationResult:
        """
        Processa o início de conversa de suporte.

        Args:
            command: Comando com dados para início da conversa

        Returns:
            SupportConversationResult: Resultado da operação
        """
        logger.info(f"Iniciando conversa de suporte para usuário {command.username} (ID: {command.user_id})")

        try:
            user_id = UserId(command.user_id)

            # 1. Busca usuário
            user = await self._user_repository.find_by_id(user_id)
            if not user:
                return SupportConversationResult(
                    success=False,
                    message="❌ Usuário não encontrado. Use /start para se registrar.",
                    reason="user_not_found"
                )

            # 2. Verifica se usuário pode criar tickets
            if not user.can_create_ticket():
                return SupportConversationResult(
                    success=False,
                    message="❌ Sua conta não está ativa para criar tickets de suporte.",
                    reason="user_not_active"
                )

            # 3. Verifica se já tem conversa ativa
            existing_conversation = await self._conversation_repository.find_active_by_user(user_id)
            if existing_conversation:
                progress = existing_conversation.get_progress_percentage()
                next_input = existing_conversation.get_next_expected_input()

                return SupportConversationResult(
                    success=False,
                    message=(
                        f"💬 **Você já tem um formulário de suporte em andamento**\n\n"
                        f"📊 **Progresso:** {progress}%\n"
                        f"➡️ **Próximo passo:** {next_input}\n\n"
                        f"Continue preenchendo o formulário ou use /cancelar_suporte para cancelar."
                    ),
                    conversation=existing_conversation,
                    reason="conversation_already_active"
                )

            # 4. Verifica limite diário (regra anti-spam)
            # TODO: Implementar verificação de limite diário
            # daily_tickets = await self._ticket_repository.count_daily_tickets_by_user(user_id)
            # if daily_tickets >= 3:
            #     return SupportConversationResult(...)

            # 5. Cria nova conversa
            conversation = SupportConversation(
                conversation_id=None,  # Será gerado automaticamente
                user=user
            )

            # 6. Salva conversa
            await self._conversation_repository.save(conversation)

            logger.info(f"Conversa de suporte iniciada: {conversation.id} para usuário {command.user_id}")

            return SupportConversationResult(
                success=True,
                message=self._format_welcome_message(user.client_name),
                conversation=conversation
            )

        except ValidationError as e:
            logger.error(f"Erro de validação ao iniciar conversa: {e}")
            return SupportConversationResult(
                success=False,
                message="❌ Dados inválidos fornecidos.",
                reason="validation_error"
            )

        except Exception as e:
            logger.error(f"Erro inesperado ao iniciar conversa de suporte: {e}")
            return SupportConversationResult(
                success=False,
                message="❌ Erro interno do sistema. Tente novamente mais tarde.",
                reason="internal_error"
            )

    def _format_welcome_message(self, client_name: str) -> str:
        """Formata mensagem de boas-vindas do suporte."""
        return (
            f"🎮 **BEM-VINDO AO SUPORTE GAMER ONCABO** 🎮\n\n"
            f"Olá, **{client_name}**! 👋\n\n"
            f"Vou te ajudar a abrir um chamado técnico de forma rápida e eficiente.\n\n"
            f"📋 **COMO FUNCIONA:**\n"
            f"• Formulário rápido com 6 etapas\n"
            f"• Você pode anexar prints/fotos\n"
            f"• Atendimento especializado em gaming\n\n"
            f"🚀 **VAMOS COMEÇAR!**\n\n"
            f"**1/6 - Qual é a categoria do seu problema?**\n\n"
            f"Escolha uma das opções abaixo:"
        )

    def _format_anti_spam_message(self, existing_tickets: int, max_daily: int) -> str:
        """Formata mensagem de limite anti-spam."""
        return (
            f"⏳ **LIMITE DIÁRIO ATINGIDO**\n\n"
            f"Você já criou **{existing_tickets}** tickets hoje.\n"
            f"Limite diário: **{max_daily}** tickets.\n\n"
            f"💡 **Sugestões:**\n"
            f"• Verifique se seus tickets anteriores foram respondidos\n"
            f"• Aguarde até amanhã para criar novos tickets\n"
            f"• Para emergências, entre em contato por telefone\n\n"
            f"🔄 **Limite será resetado à meia-noite**"
        )