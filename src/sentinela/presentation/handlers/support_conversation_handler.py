"""
Support Conversation Handler.

Handler do Telegram para gerenciar o fluxo completo
do formulário conversacional de suporte.
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...application.use_cases.support_form_use_case import (
    SupportFormUseCase,
    SupportFormStep,
    SupportFormResult
)

logger = logging.getLogger(__name__)


class SupportConversationHandler:
    """
    Handler para conversações de suporte.

    Gerencia todo o fluxo do formulário conversacional,
    desde o início até a criação do ticket.
    """

    def __init__(
        self,
        support_form_use_case: SupportFormUseCase,
        tech_channel_id: Optional[int] = None
    ):
        """
        Inicializa o handler.

        Args:
            support_form_use_case: Use case do formulário de suporte
            tech_channel_id: ID do canal técnico para notificações
        """
        self.support_form_use_case = support_form_use_case
        self.tech_channel_id = tech_channel_id

    async def handle_start_support(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Inicia novo formulário de suporte.

        Args:
            update: Update do Telegram
            context: Context do Telegram
        """
        try:
            user = update.effective_user
            logger.info(f"Iniciando suporte para usuário {user.id} (@{user.username})")

            # Inicia conversa via use case
            result = await self.support_form_use_case.start_conversation(
                user_id=user.id,
                username=user.username or user.first_name
            )

            # Envia resposta
            if result.success:
                keyboard = self._build_keyboard(result.keyboard_options)
                await update.message.reply_text(
                    result.message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    result.message,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Erro ao iniciar suporte: {e}")
            await update.message.reply_text(
                "❌ Erro ao iniciar suporte. Tente novamente em alguns instantes."
            )

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Processa callbacks de botões inline.

        Args:
            update: Update do Telegram
            context: Context do Telegram
        """
        query = update.callback_query
        await query.answer()

        try:
            user = query.from_user
            callback_data = query.data

            logger.info(f"Callback do usuário {user.id}: {callback_data}")

            # Processa baseado no tipo de callback
            if callback_data.startswith("category_"):
                await self._handle_category_selection(query, context, callback_data)

            elif callback_data.startswith("game_"):
                await self._handle_game_selection(query, context, callback_data)

            elif callback_data.startswith("timing_"):
                await self._handle_timing_selection(query, context, callback_data)

            elif callback_data.startswith("attachment_"):
                await self._handle_attachment_action(query, context, callback_data)

            elif callback_data.startswith("confirm_"):
                await self._handle_confirmation(query, context, callback_data)

            else:
                logger.warning(f"Callback não reconhecido: {callback_data}")
                await query.edit_message_text("❌ Ação não reconhecida.")

        except Exception as e:
            logger.error(f"Erro ao processar callback: {e}")
            await query.edit_message_text(
                "❌ Erro ao processar sua ação. Tente novamente."
            )

    async def handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Processa mensagens de texto do usuário.

        Args:
            update: Update do Telegram
            context: Context do Telegram
        """
        try:
            user = update.effective_user
            message_text = update.message.text

            logger.info(f"Mensagem do usuário {user.id}: {message_text[:50]}...")

            # Processa entrada de descrição
            result = await self.support_form_use_case.process_description(
                user_id=user.id,
                description=message_text
            )

            # Envia resposta
            keyboard = self._build_keyboard(result.keyboard_options)
            await update.message.reply_text(
                result.message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar sua mensagem. Tente novamente."
            )

    async def handle_photo(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Processa envio de fotos/screenshots.

        Args:
            update: Update do Telegram
            context: Context do Telegram
        """
        try:
            user = update.effective_user
            photo = update.message.photo[-1]  # Pega a maior resolução

            logger.info(f"Foto recebida do usuário {user.id}: {photo.file_id}")

            # Processa anexo
            result = await self.support_form_use_case.add_attachment(
                user_id=user.id,
                file_id=photo.file_id,
                file_type="photo"
            )

            # Envia resposta
            keyboard = self._build_keyboard(result.keyboard_options)
            await update.message.reply_text(
                result.message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao processar foto: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar foto. Tente novamente."
            )

    async def handle_cancel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Cancela formulário de suporte.

        Args:
            update: Update do Telegram
            context: Context do Telegram
        """
        try:
            user = update.effective_user
            logger.info(f"Cancelando suporte para usuário {user.id}")

            result = await self.support_form_use_case.cancel_conversation(user.id)

            await update.message.reply_text(
                result.message,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao cancelar suporte: {e}")
            await update.message.reply_text(
                "❌ Erro ao cancelar. Tente /suporte para começar novamente."
            )

    # Private helper methods

    async def _handle_category_selection(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de categoria."""
        user = query.from_user
        category = callback_data.replace("category_", "")

        result = await self.support_form_use_case.process_category(
            user_id=user.id,
            category=category
        )

        keyboard = self._build_keyboard(result.keyboard_options)
        await query.edit_message_text(
            result.message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def _handle_game_selection(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de jogo."""
        user = query.from_user
        game = callback_data.replace("game_", "")

        result = await self.support_form_use_case.process_game(
            user_id=user.id,
            game=game
        )

        keyboard = self._build_keyboard(result.keyboard_options)

        if result.next_step == SupportFormStep.DESCRIPTION_INPUT:
            # Remove teclado inline para input de texto
            await query.edit_message_text(
                result.message,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                result.message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    async def _handle_timing_selection(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de timing."""
        user = query.from_user
        timing = callback_data.replace("timing_", "")

        result = await self.support_form_use_case.process_timing(
            user_id=user.id,
            timing=timing
        )

        # Remove teclado inline para input de texto
        await query.edit_message_text(
            result.message,
            parse_mode='Markdown'
        )

    async def _handle_attachment_action(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa ações de anexos."""
        user = query.from_user

        if callback_data == "attachment_skip":
            # Pula anexos
            result = await self.support_form_use_case.skip_attachments(user.id)

            keyboard = self._build_keyboard(result.keyboard_options)
            await query.edit_message_text(
                result.message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        elif callback_data == "attachment_send":
            # Aguarda envio de anexo
            await query.answer("📎 Envie suas fotos/screenshots agora")

    async def _handle_confirmation(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa confirmação de criação do ticket."""
        user = query.from_user

        if callback_data == "confirm_create":
            # Cria o ticket
            result = await self.support_form_use_case.create_ticket(user.id)

            await query.edit_message_text(
                result.message,
                parse_mode='Markdown'
            )

            # Envia notificação técnica se canal configurado
            if result.success and result.ticket and self.tech_channel_id:
                await self._send_tech_notification(
                    context,
                    result.ticket,
                    user
                )

        elif callback_data == "confirm_cancel":
            # Cancela criação
            result = await self.support_form_use_case.cancel_conversation(user.id)

            await query.edit_message_text(
                result.message,
                parse_mode='Markdown'
            )

    async def _send_tech_notification(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        ticket,
        user
    ) -> None:
        """Envia notificação para canal técnico."""
        try:
            protocol = ticket.get_display_protocol()

            notification = (
                f"🎫 **NOVO CHAMADO - BOT CONVERSACIONAL**\n\n"
                f"📋 **Protocolo:** `{protocol}`\n"
                f"👤 **Usuário:** {user.first_name} (@{user.username or 'sem username'})\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"📊 **Status:** {ticket.status.value}\n"
                f"🎮 **Jogo:** {ticket.affected_game.display_name}\n"
                f"🔸 **Categoria:** {ticket.category.display_name}\n\n"
                f"📝 **Descrição:**\n{ticket.description[:200]}{'...' if len(ticket.description) > 200 else ''}\n\n"
                f"🕒 **Criado em:** {ticket.created_at.strftime('%d/%m/%Y às %H:%M')}\n\n"
                f"🔗 **Responder no tópico de Suporte Gamer**"
            )

            await context.bot.send_message(
                chat_id=self.tech_channel_id,
                text=notification,
                parse_mode='Markdown'
            )

            logger.info(f"Notificação técnica enviada para ticket {protocol}")

        except Exception as e:
            logger.error(f"Erro ao enviar notificação técnica: {e}")

    def _build_keyboard(
        self,
        options: list
    ) -> Optional[InlineKeyboardMarkup]:
        """
        Constrói teclado inline a partir das opções.

        Args:
            options: Lista de opções {text, callback_data}

        Returns:
            InlineKeyboardMarkup: Teclado formatado ou None
        """
        if not options:
            return None

        # Cria botões (2 por linha)
        keyboard = []
        row = []

        for option in options:
            button = InlineKeyboardButton(
                text=option["text"],
                callback_data=option["callback_data"]
            )
            row.append(button)

            # Adiciona linha quando tiver 2 botões
            if len(row) == 2:
                keyboard.append(row)
                row = []

        # Adiciona última linha se tiver botões restantes
        if row:
            keyboard.append(row)

        return InlineKeyboardMarkup(keyboard)