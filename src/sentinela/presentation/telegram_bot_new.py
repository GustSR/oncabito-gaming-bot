
"""
Registra os handlers do Telegram Bot para a nova arquitetura.
"""

import logging
from telegram.ext import Application
from src.sentinela.core.config import TELEGRAM_TOKEN

# Cria a instância principal da aplicação do bot
application = Application.builder().token(TELEGRAM_TOKEN).build()

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, filters

from src.sentinela.presentation.handlers.telegram_bot_handler import TelegramBotHandler

logger = logging.getLogger(__name__)

def register_handlers(app: Application) -> None:
    """
    Registra todos os handlers da aplicação na nova arquitetura.
    """
    logger.info("Registrando handlers da nova arquitetura...")

    # Instancia o handler principal da apresentação
    handler = TelegramBotHandler()

    # Comandos de usuário
    # /start: APENAS no privado (não funciona no grupo)
    app.add_handler(CommandHandler("start", handler.handle_start_command, filters=filters.ChatType.PRIVATE))
    # /suporte e /status: funcionam no grupo e no privado
    app.add_handler(CommandHandler("suporte", handler.handle_support_command))
    app.add_handler(CommandHandler("status", handler.handle_status_command))

    # Callbacks de botões
    app.add_handler(CallbackQueryHandler(handler.handle_callback_query))

    # Handler de novos membros
    app.add_handler(ChatMemberHandler(handler.handle_new_member, ChatMemberHandler.CHAT_MEMBER))

    # Mensagens de texto (para CPF, descrição de suporte, etc.)
    # IMPORTANTE: Apenas no privado! Bot não responde mensagens em grupos/canais
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handler.handle_text_message))

    # Mensagens de foto (para anexos de suporte)
    # IMPORTANTE: Apenas no privado! Bot não responde mensagens em grupos/canais
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handler.handle_photo_message))

    # Handler de erros
    app.add_error_handler(handler.handle_error)

    logger.info("Handlers da nova arquitetura registrados com sucesso.")
