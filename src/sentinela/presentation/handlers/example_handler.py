"""
Exemplo de Handler usando a nova arquitetura.

Demonstra como um handler do Telegram deve ser estruturado
na nova arquitetura em camadas.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...infrastructure.config.dependency_injection import dependency_injected
from ...application.commands.create_user_command import CreateUserCommand
from ...application.commands.create_user_handler import CreateUserHandler, UserAlreadyExistsError
from ...application.queries.get_user_query import GetUserQuery
from ...application.queries.get_user_handler import GetUserHandler
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.base import ValidationError

logger = logging.getLogger(__name__)


class UserHandlers:
    """
    Handlers para operações de usuário.

    Demonstra o padrão da nova arquitetura:
    1. Handler recebe input do Telegram
    2. Mapeia para Command/Query
    3. Executa via Application Layer
    4. Mapeia resposta para formato Telegram
    5. Envia resposta
    """

    @staticmethod
    @dependency_injected
    async def handle_start_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_repository: UserRepository  # Injetado automaticamente
    ) -> None:
        """
        Handler para comando /start.

        Args:
            update: Update do Telegram
            context: Context do bot
            user_repository: Repository injetado automaticamente
        """
        user = update.effective_user
        chat = update.effective_chat

        logger.info(f"Start command from user {user.username} ({user.id})")

        try:
            # === 1. VALIDAÇÃO DE INPUT ===
            if not user or not chat:
                await update.message.reply_text("❌ Erro: informações do usuário não disponíveis")
                return

            # === 2. QUERY: Verifica se usuário já existe ===
            query = GetUserQuery(user_id=user.id)
            query_handler = GetUserHandler(user_repository)
            existing_user = await query_handler.handle(query)

            if existing_user:
                # Usuário já existe
                status_emoji = "✅" if existing_user.is_active() else "⏳"
                await update.message.reply_text(
                    f"{status_emoji} Olá, {existing_user.client_name}!\n\n"
                    f"Você já está registrado no sistema.\n"
                    f"Status: {existing_user.status.value}\n\n"
                    f"Use /help para ver comandos disponíveis."
                )
                return

            # === 3. NOVO USUÁRIO: Inicia processo de verificação ===
            await update.message.reply_text(
                "👋 Bem-vindo ao OnCabo Gaming!\n\n"
                "Para acessar o sistema, preciso verificar seu CPF.\n"
                "Por favor, envie seu CPF (apenas números):"
            )

            # Aqui normalmente salvaria estado da conversa
            # Na nova arquitetura, isso seria um ConversationState entity

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text(
                "❌ Erro interno. Tente novamente mais tarde."
            )

    @staticmethod
    @dependency_injected
    async def handle_cpf_verification(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_repository: UserRepository  # Injetado automaticamente
    ) -> None:
        """
        Handler para verificação de CPF.

        Args:
            update: Update do Telegram
            context: Context do bot
            user_repository: Repository injetado automaticamente
        """
        user = update.effective_user
        message_text = update.message.text

        logger.info(f"CPF verification from user {user.username} ({user.id})")

        try:
            # === 1. VALIDAÇÃO DE INPUT ===
            if not message_text or len(message_text.strip()) == 0:
                await update.message.reply_text(
                    "❌ Por favor, envie um CPF válido (apenas números)."
                )
                return

            # === 2. COMMAND: Cria usuário ===
            command = CreateUserCommand(
                user_id=user.id,
                username=user.username or f"user_{user.id}",
                cpf=message_text.strip(),
                client_name="Nome Temporário",  # Seria obtido do HubSoft
            )

            command_handler = CreateUserHandler(user_repository)
            new_user = await command_handler.handle(command)

            # === 3. RESPOSTA DE SUCESSO ===
            await update.message.reply_text(
                f"✅ CPF verificado com sucesso!\n\n"
                f"👤 **Dados registrados:**\n"
                f"Nome: {new_user.client_name}\n"
                f"CPF: {new_user.cpf.masked()}\n"
                f"Status: {new_user.status.value}\n\n"
                f"Aguarde a ativação da sua conta."
            )

        except ValidationError as e:
            # Erro de validação de domínio
            await update.message.reply_text(
                f"❌ CPF inválido: {e.message}\n\n"
                f"Por favor, envie um CPF válido (11 dígitos)."
            )

        except UserAlreadyExistsError:
            # Usuário já existe
            await update.message.reply_text(
                "❌ Este usuário já está registrado no sistema.\n\n"
                "Use /start para verificar seu status."
            )

        except Exception as e:
            logger.error(f"Error in CPF verification: {e}")
            await update.message.reply_text(
                "❌ Erro ao verificar CPF. Tente novamente mais tarde."
            )

    @staticmethod
    @dependency_injected
    async def handle_status_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_repository: UserRepository  # Injetado automaticamente
    ) -> None:
        """
        Handler para comando /status.

        Args:
            update: Update do Telegram
            context: Context do bot
            user_repository: Repository injetado automaticamente
        """
        user = update.effective_user

        logger.info(f"Status command from user {user.username} ({user.id})")

        try:
            # === 1. QUERY: Busca usuário ===
            query = GetUserQuery(user_id=user.id)
            query_handler = GetUserHandler(user_repository)
            current_user = await query_handler.handle(query)

            if not current_user:
                await update.message.reply_text(
                    "❌ Usuário não encontrado.\n\n"
                    "Use /start para se registrar."
                )
                return

            # === 2. FORMATA RESPOSTA ===
            status_emoji = {
                "active": "✅",
                "inactive": "❌",
                "pending_verification": "⏳",
                "suspended": "🚫"
            }.get(current_user.status.value, "❓")

            service_info = ""
            if current_user.service_info:
                service_info = (
                    f"🔌 **Serviço:** {current_user.service_info.name}\n"
                    f"📊 **Status do Serviço:** {current_user.service_info.status}\n"
                )

            await update.message.reply_text(
                f"{status_emoji} **STATUS DA CONTA**\n\n"
                f"👤 **Nome:** {current_user.client_name}\n"
                f"🆔 **CPF:** {current_user.cpf.masked()}\n"
                f"📱 **Username:** @{current_user.username}\n"
                f"🔄 **Status:** {current_user.status.value}\n"
                f"{service_info}"
                f"📅 **Criado em:** {current_user.created_at.strftime('%d/%m/%Y às %H:%M')}\n"
                f"🔄 **Atualizado em:** {current_user.updated_at.strftime('%d/%m/%Y às %H:%M')}"
            )

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(
                "❌ Erro ao consultar status. Tente novamente mais tarde."
            )


# === EXEMPLO DE USO ===

def register_example_handlers(application):
    """
    Registra os handlers de exemplo.

    Args:
        application: Application do python-telegram-bot
    """
    from telegram.ext import CommandHandler, MessageHandler, filters

    # Comandos
    application.add_handler(CommandHandler("start", UserHandlers.handle_start_command))
    application.add_handler(CommandHandler("status", UserHandlers.handle_status_command))

    # Mensagens de CPF (exemplo - seria mais complexo na realidade)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, UserHandlers.handle_cpf_verification)
    )