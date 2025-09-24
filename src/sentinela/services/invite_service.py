import logging
import time
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from src.sentinela.core.config import (
    TELEGRAM_TOKEN,
    TELEGRAM_GROUP_ID,
    INVITE_LINK_EXPIRE_TIME,
    INVITE_LINK_MEMBER_LIMIT
)

logger = logging.getLogger(__name__)

async def create_temporary_invite_link(user_id: int, username: str) -> str | None:
    """
    Cria um link de convite temporário para o grupo da OnCabo.

    Args:
        user_id: ID do usuário do Telegram
        username: Nome de usuário do Telegram

    Returns:
        Link de convite temporário ou None em caso de erro
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        # Calcula o tempo de expiração usando um timestamp Unix puro
        expire_date = int(time.time()) + INVITE_LINK_EXPIRE_TIME

        logger.info(f"Criando link de convite temporário para {username} (ID: {user_id})")

        # Cria o link de convite com limite de uso e tempo de expiração
        invite_link = await bot.create_chat_invite_link(
            chat_id=TELEGRAM_GROUP_ID,
            name=f"Acesso {username} - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            expire_date=expire_date,
            member_limit=INVITE_LINK_MEMBER_LIMIT,
            creates_join_request=False
        )

        logger.info(f"Link de convite criado com sucesso: {invite_link.invite_link}")
        return invite_link.invite_link

    except TelegramError as e:
        logger.error(f"Erro do Telegram ao criar link de convite para {username}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao criar link de convite para {username}: {e}")
        return None

async def revoke_invite_link(invite_link: str) -> bool:
    """
    Revoga um link de convite específico.

    Args:
        invite_link: URL do link de convite a ser revogado

    Returns:
        True se revogado com sucesso, False caso contrário
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        logger.info(f"Revogando link de convite: {invite_link}")

        await bot.revoke_chat_invite_link(
            chat_id=TELEGRAM_GROUP_ID,
            invite_link=invite_link
        )

        logger.info("Link de convite revogado com sucesso")
        return True

    except TelegramError as e:
        logger.error(f"Erro do Telegram ao revogar link de convite: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao revogar link de convite: {e}")
        return False
