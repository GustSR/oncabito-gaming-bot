
"""
Registra os handlers do Telegram Bot para a nova arquitetura.
"""

import logging
from telegram.ext import Application
from ..core.config import TELEGRAM_TOKEN

# Cria a instância principal da aplicação do bot
application = Application.builder().token(TELEGRAM_TOKEN).build()

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, filters

from .handlers.telegram_bot_handler import TelegramBotHandler

logger = logging.getLogger(__name__)

def register_handlers(app: Application) -> None:
    """
    Registra todos os handlers da aplicação na nova arquitetura.
    """
    logger.info("Registrando handlers da nova arquitetura...")

    # Instancia o handler principal da apresentação
    handler = TelegramBotHandler()

    # Comandos de usuário
    app.add_handler(CommandHandler("start", handler.handle_start_command))
    app.add_handler(CommandHandler("suporte", handler.handle_support_command))
    app.add_handler(CommandHandler("status", handler.handle_status_command))

    # Comandos de admin
    app.add_handler(CommandHandler("admin", handler.handle_admin_command))

    # Callbacks de botões
    app.add_handler(CallbackQueryHandler(handler.handle_callback_query))

    # Handler de novos membros
    app.add_handler(ChatMemberHandler(handler.handle_new_member, ChatMemberHandler.CHAT_MEMBER))

    # Mensagens de texto (para CPF, descrição de suporte, etc.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_text_message))

    # Mensagens de foto (para anexos de suporte)
    app.add_handler(MessageHandler(filters.PHOTO, handler.handle_photo_message))

    # Handler de erros
    app.add_error_handler(handler.handle_error)

    logger.info("Handlers da nova arquitetura registrados com sucesso.")
