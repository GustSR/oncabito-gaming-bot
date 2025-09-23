import logging
from telegram import Bot, ChatPermissions
from telegram.error import TelegramError
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

logger = logging.getLogger(__name__)

class PermissionsService:
    """Serviço para gerenciar permissões de usuários no grupo."""

    def __init__(self):
        self.bot = Bot(token=TELEGRAM_TOKEN)

    async def grant_topic_access(self, user_id: int, username: str) -> bool:
        """
        Concede acesso aos tópicos de gaming após aceitar regras.

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            bool: True se concedeu acesso com sucesso
        """
        try:
            async with self.bot:
                # Opção 1: Promover para cargo especial (se existir)
                try:
                    await self.bot.promote_chat_member(
                        chat_id=TELEGRAM_GROUP_ID,
                        user_id=user_id,
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True
                    )
                    logger.info(f"Usuário {username} promovido com sucesso")
                    return True
                except TelegramError as e:
                    if "not enough rights" in str(e).lower():
                        logger.warning(f"Bot não tem permissão para promover usuários")
                        # Opção 2: Usar restrições específicas por tópico
                        return await self.set_topic_permissions(user_id, username)
                    else:
                        raise e

        except Exception as e:
            logger.error(f"Erro ao conceder acesso aos tópicos para {username}: {e}")
            return False

    async def set_topic_permissions(self, user_id: int, username: str) -> bool:
        """
        Define permissões específicas para tópicos (método alternativo).

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            bool: True se definiu permissões com sucesso
        """
        try:
            # O Telegram não permite definir permissões por tópico via API
            # Esta é uma limitação da API atual
            # Solução: usar cargos/roles no grupo

            logger.info(f"Tentando definir permissões para {username} via método alternativo")

            # Por enquanto, apenas logamos que o usuário foi "liberado"
            # A configuração real precisa ser feita manualmente no Telegram
            await self.notify_admins_about_verification(user_id, username)

            return True

        except Exception as e:
            logger.error(f"Erro ao definir permissões para {username}: {e}")
            return False

    async def notify_admins_about_verification(self, user_id: int, username: str) -> bool:
        """
        Notifica administradores que usuário foi verificado e precisa de acesso.

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            bool: True se notificou com sucesso
        """
        try:
            from src.sentinela.services.group_service import get_group_administrators, send_private_message

            administrators = await get_group_administrators()
            if not administrators:
                return False

            message = f"✅ <b>USUÁRIO VERIFICADO - LIBERAR ACESSO</b>\n\n"
            message += f"👤 <b>Usuário:</b> {username}\n"
            message += f"🆔 <b>ID:</b> {user_id}\n"
            message += f"📋 <b>Status:</b> Aceitou regras\n\n"
            message += f"🔧 <b>Ação necessária:</b>\n"
            message += f"• Adicione ao cargo 'Gamer Verificado'\n"
            message += f"• Ou libere acesso aos tópicos manualmente\n\n"
            message += f"🎮 <b>Tópicos para liberar:</b>\n"
            message += f"• 🎮 Jogos FPS & Battle Royale\n"
            message += f"• 🧙 RPG & MMORPG\n"
            message += f"• ⚽️ Esportes & Corrida\n"
            message += f"• 🕹 Retro & Indie\n"
            message += f"• 🎧 Setup & Periféricos\n\n"
            message += f"🤖 <i>Sistema Sentinela - OnCabo</i>"

            success_count = 0
            for admin in administrators:
                if await send_private_message(admin['user_id'], message):
                    success_count += 1

            logger.info(f"Notificação de verificação enviada para {success_count} administradores")
            return success_count > 0

        except Exception as e:
            logger.error(f"Erro ao notificar administradores sobre verificação: {e}")
            return False

    async def revoke_topic_access(self, user_id: int, username: str) -> bool:
        """
        Revoga acesso aos tópicos (para usuários que violaram regras).

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            bool: True se revogou acesso com sucesso
        """
        try:
            async with self.bot:
                # Remove promoções especiais
                await self.bot.promote_chat_member(
                    chat_id=TELEGRAM_GROUP_ID,
                    user_id=user_id,
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_polls=False,
                    can_send_other_messages=False
                )

                logger.info(f"Acesso aos tópicos revogado para {username}")
                return True

        except Exception as e:
            logger.error(f"Erro ao revogar acesso para {username}: {e}")
            return False

    async def get_user_permissions(self, user_id: int) -> dict:
        """
        Obtém permissões atuais do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            dict: Permissões do usuário
        """
        try:
            async with self.bot:
                member = await self.bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)

                return {
                    'status': member.status,
                    'can_send_messages': getattr(member, 'can_send_messages', True),
                    'can_send_media_messages': getattr(member, 'can_send_media_messages', True),
                    'is_promoted': member.status in ['administrator', 'creator']
                }

        except Exception as e:
            logger.error(f"Erro ao obter permissões do usuário {user_id}: {e}")
            return {}

# Instância global do serviço
permissions_service = PermissionsService()