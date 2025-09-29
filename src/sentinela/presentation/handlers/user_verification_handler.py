"""
Handler para verificação de usuários via CPF.

Substitui a funcionalidade do user_service.process_user_verification
usando a nova arquitetura em camadas.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...infrastructure.config.dependency_injection import dependency_injected
from ...application.commands.verify_user_command import VerifyUserCommand
from ...application.commands.verify_user_handler import VerifyUserHandler
from ...domain.value_objects.base import ValidationError

logger = logging.getLogger(__name__)


class UserVerificationHandlers:
    """
    Handlers para verificação de usuários.

    Esta classe substitui as funcionalidades do user_service.py
    seguindo os princípios da nova arquitetura.
    """

    @staticmethod
    @dependency_injected
    async def handle_user_verification(
        cpf: str,
        user_id: int,
        username: str,
        verify_user_handler: VerifyUserHandler  # Injetado automaticamente
    ) -> str:
        """
        Processa verificação de usuário via CPF.

        Args:
            cpf: CPF do usuário
            user_id: ID do usuário no Telegram
            username: Username do usuário
            verify_user_handler: Handler injetado automaticamente

        Returns:
            str: Mensagem de resposta para o usuário

        Note:
            Esta função substitui user_service.process_user_verification
            mantendo a mesma interface pública para compatibilidade.
        """
        logger.info(f"Processando verificação para usuário {username} (ID: {user_id}) via nova arquitetura")

        try:
            # Cria command com dados validados
            command = VerifyUserCommand(
                cpf=cpf,
                user_id=user_id,
                username=username or f"user_{user_id}"
            )

            # Executa via application layer
            result = await verify_user_handler.handle(command)

            # Retorna mensagem formatada
            return result.message

        except ValidationError as e:
            logger.error(f"Erro de validação durante verificação: {e}")
            return f"❌ Dados inválidos: {e.message}"

        except Exception as e:
            logger.error(f"Erro inesperado durante verificação: {e}")
            return "❌ Erro interno durante verificação. Tente novamente mais tarde."

    @staticmethod
    @dependency_injected
    async def handle_telegram_verification(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        verify_user_handler: VerifyUserHandler  # Injetado automaticamente
    ) -> None:
        """
        Handler para verificação via comando Telegram.

        Args:
            update: Update do Telegram
            context: Context do bot
            verify_user_handler: Handler injetado automaticamente
        """
        user = update.effective_user

        if not user:
            await update.message.reply_text("❌ Erro: informações do usuário não disponíveis")
            return

        logger.info(f"Verificação via Telegram para usuário {user.username} (ID: {user.id})")

        try:
            # Extrai CPF do contexto (assumindo que foi fornecido previamente)
            if not context.args or len(context.args) == 0:
                await update.message.reply_text(
                    "❌ Por favor, forneça seu CPF.\n"
                    "Uso: /verificar <cpf>"
                )
                return

            cpf = context.args[0].strip()

            # Processa verificação
            result_message = await UserVerificationHandlers.handle_user_verification(
                cpf=cpf,
                user_id=user.id,
                username=user.username or f"user_{user.id}",
                verify_user_handler=verify_user_handler
            )

            # Envia resposta
            await update.message.reply_text(result_message, parse_mode='HTML')

        except Exception as e:
            logger.error(f"Erro no handler Telegram de verificação: {e}")
            await update.message.reply_text(
                "❌ Erro interno. Tente novamente mais tarde."
            )