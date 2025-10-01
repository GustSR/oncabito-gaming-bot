"""
Scheduled Task Event Handlers.

Handlers para eventos de tarefas agendadas.
"""

import logging
from typing import Any

from ...domain.events.system_events import ScheduledTaskTriggeredEvent
from ...application.use_cases.member_verification_use_case import MemberVerificationUseCase

logger = logging.getLogger(__name__)


class MemberCPFCheckTaskHandler:
    """
    Handler para tarefa de verificação de CPF de membros.

    Escuta evento ScheduledTaskTriggeredEvent e executa verificação
    quando task_id = "check_member_cpf_daily".
    """

    def __init__(
        self,
        member_verification_use_case: MemberVerificationUseCase,
        bot_instance: Any = None  # Instância do bot Telegram
    ):
        """
        Inicializa o handler.

        Args:
            member_verification_use_case: Use case de verificação de membros
            bot_instance: Instância do bot Telegram (para acessar API)
        """
        self.member_verification_use_case = member_verification_use_case
        self.bot_instance = bot_instance

    async def handle(self, event: ScheduledTaskTriggeredEvent) -> None:
        """
        Processa evento de tarefa agendada.

        Args:
            event: Evento de tarefa triggered
        """
        if event.task_id != "check_member_cpf_daily":
            return

        logger.info(f"🔍 Executando verificação diária de CPF de membros - {event.triggered_at}")

        try:
            if not self.bot_instance:
                logger.error("Bot instance não configurada para verificação de membros")
                return

            # Obtém informações do grupo
            group_id = self.bot_instance.group_id
            admin_ids = self.bot_instance.admin_user_ids

            logger.info(f"Obtendo lista de membros do grupo {group_id}")

            # Lista membros do grupo via Telegram API
            # Nota: Para grupos grandes, usar get_chat_administrators + iterar membros
            try:
                # Obtém administradores
                chat_admins = await self.bot_instance.application.bot.get_chat_administrators(group_id)

                logger.info(f"Encontrados {len(chat_admins)} administradores")

                # Em grupos grandes, precisamos de outra estratégia
                # Por ora, vamos apenas verificar usuários no banco que estão ativos
                # e não têm CPF vinculado

                # Busca usuários sem CPF no banco
                user_repo = self.bot_instance.container.get("user_repository")
                users_without_cpf = await user_repo.find_users_without_cpf()

                logger.info(f"Encontrados {len(users_without_cpf)} usuários sem CPF no banco")

                # Para cada usuário sem CPF, envia solicitação
                for user in users_without_cpf:
                    # Pula admins
                    if user.user_id.value in admin_ids:
                        continue

                    logger.info(f"Solicitando CPF de: {user.username} ({user.user_id.value})")

                    try:
                        # Envia mensagem privada solicitando CPF
                        message = await self.member_verification_use_case.get_cpf_verification_message()

                        await self.bot_instance.application.bot.send_message(
                            chat_id=user.user_id.value,
                            text=message,
                            parse_mode='Markdown'
                        )

                        logger.info(f"Mensagem de verificação enviada para {user.user_id.value}")

                    except Exception as dm_error:
                        logger.warning(
                            f"Não foi possível enviar DM para {user.user_id.value}: {dm_error}"
                        )
                        # Continua para próximo usuário

                logger.info("✅ Verificação diária de CPF concluída")

            except Exception as api_error:
                logger.error(f"Erro ao acessar Telegram API: {api_error}")

        except Exception as e:
            logger.error(f"❌ Erro ao executar verificação diária de CPF: {e}")


class InviteCleanupTaskHandler:
    """
    Handler para tarefa de limpeza de convites expirados.

    Escuta evento ScheduledTaskTriggeredEvent e limpa convites
    quando task_id = "cleanup_expired_invites".
    """

    def __init__(self, bot_instance: Any = None):
        """
        Inicializa o handler.

        Args:
            bot_instance: Instância do bot Telegram
        """
        self.bot_instance = bot_instance

    async def handle(self, event: ScheduledTaskTriggeredEvent) -> None:
        """
        Processa evento de limpeza de convites.

        Args:
            event: Evento de tarefa triggered
        """
        if event.task_id != "cleanup_expired_invites":
            return

        logger.info(f"🧹 Executando limpeza de convites expirados - {event.triggered_at}")

        try:
            if not self.bot_instance:
                logger.error("Bot instance não configurada")
                return

            # Obtém repositório de convites
            group_invite_repo = self.bot_instance.container.get("group_invite_repository")

            # Limpa convites com mais de 30 dias
            deleted_count = await group_invite_repo.cleanup_old_invites(days=30)

            logger.info(f"✅ Limpeza concluída: {deleted_count} convites removidos")

        except Exception as e:
            logger.error(f"❌ Erro ao limpar convites expirados: {e}")


class VerificationExpiryTaskHandler:
    """
    Handler para tarefa de expiração de verificações de CPF.

    Escuta evento ScheduledTaskTriggeredEvent e expira verificações antigas
    quando task_id = "expire_old_verifications".
    """

    def __init__(self, bot_instance: Any = None):
        """
        Inicializa o handler.

        Args:
            bot_instance: Instância do bot Telegram
        """
        self.bot_instance = bot_instance

    async def handle(self, event: ScheduledTaskTriggeredEvent) -> None:
        """
        Processa evento de expiração de verificações.

        Args:
            event: Evento de tarefa triggered
        """
        if event.task_id != "expire_old_verifications":
            return

        logger.info(f"⏰ Executando expiração de verificações antigas - {event.triggered_at}")

        try:
            if not self.bot_instance:
                logger.error("Bot instance não configurada")
                return

            # Obtém use case de CPF
            cpf_use_case = self.bot_instance.container.get("cpf_verification_use_case")

            # Processa verificações expiradas
            result = await cpf_use_case.process_expired_verifications()

            if result.success:
                expired_count = result.data.get('expired_count', 0)
                logger.info(f"✅ Expiração concluída: {expired_count} verificações expiradas")
            else:
                logger.warning(f"⚠️ Erro ao expirar verificações: {result.message}")

        except Exception as e:
            logger.error(f"❌ Erro ao expirar verificações: {e}")
