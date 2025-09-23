import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

logger = logging.getLogger(__name__)

async def is_user_in_group(user_id: int) -> bool:
    """
    Verifica se o usuário está no grupo.

    Args:
        user_id: ID do usuário no Telegram

    Returns:
        bool: True se o usuário estiver no grupo, False caso contrário
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        # Verifica o status do membro no grupo
        member = await bot.get_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)

        # Status possíveis: 'creator', 'administrator', 'member', 'restricted', 'left', 'kicked'
        active_statuses = ['creator', 'administrator', 'member', 'restricted']

        is_active_member = member.status in active_statuses

        logger.info(f"Usuário {user_id} - Status no grupo: {member.status} - Ativo: {is_active_member}")

        return is_active_member

    except TelegramError as e:
        # Se o usuário não está no grupo, o Telegram retorna um erro
        if "user not found" in str(e).lower() or "bad request" in str(e).lower():
            logger.info(f"Usuário {user_id} não está no grupo.")
            return False
        else:
            logger.error(f"Erro do Telegram ao verificar membro {user_id}: {e}")
            return False
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar se usuário {user_id} está no grupo: {e}")
        return False

async def remove_user_from_group(user_id: int, reason: str = "Contrato inativo") -> bool:
    """
    Remove um usuário do grupo.

    Args:
        user_id: ID do usuário no Telegram
        reason: Motivo da remoção (para logs)

    Returns:
        bool: True se removeu com sucesso, False caso contrário
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        logger.info(f"Tentando remover usuário {user_id} do grupo. Motivo: {reason}")

        # Verifica se o usuário está realmente no grupo antes de tentar remover
        is_member = await is_user_in_group(user_id)
        if not is_member:
            logger.info(f"Usuário {user_id} não está no grupo, nada a remover.")
            return True

        # Remove o usuário do grupo (ban temporário)
        await bot.ban_chat_member(
            chat_id=TELEGRAM_GROUP_ID,
            user_id=user_id,
            # until_date=None significa ban permanente
            # Para un-ban automático depois de um tempo, use:
            # until_date=datetime.now() + timedelta(seconds=30)
        )

        # Desban imediatamente para permitir re-entrada no futuro se contrato for reativado
        await bot.unban_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)

        logger.info(f"Usuário {user_id} removido do grupo com sucesso. Motivo: {reason}")
        return True

    except TelegramError as e:
        if "user not found" in str(e).lower():
            logger.info(f"Usuário {user_id} não encontrado no grupo.")
            return True
        elif "not enough rights" in str(e).lower():
            logger.error(f"Bot não tem permissão para remover usuário {user_id}")
            return False
        else:
            logger.error(f"Erro do Telegram ao remover usuário {user_id}: {e}")
            return False
    except Exception as e:
        logger.error(f"Erro inesperado ao remover usuário {user_id}: {e}")
        return False

async def kick_user_from_group(user_id: int, reason: str = "Contrato inativo") -> bool:
    """
    Remove usuário do grupo de forma mais simples (apenas kick).

    Args:
        user_id: ID do usuário no Telegram
        reason: Motivo da remoção

    Returns:
        bool: True se removeu com sucesso, False caso contrário
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        logger.info(f"Removendo usuário {user_id} do grupo. Motivo: {reason}")

        # Verifica se está no grupo
        is_member = await is_user_in_group(user_id)
        if not is_member:
            logger.info(f"Usuário {user_id} não está no grupo.")
            return True

        # Remove usando kick (mais simples que ban/unban)
        result = await bot.ban_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)

        if result:
            # Permite que o usuário possa voltar no futuro
            await bot.unban_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)
            logger.info(f"Usuário {user_id} removido com sucesso.")
            return True
        else:
            logger.warning(f"Falha ao remover usuário {user_id}")
            return False

    except TelegramError as e:
        logger.error(f"Erro do Telegram ao remover usuário {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao remover usuário {user_id}: {e}")
        return False

async def get_group_info() -> dict:
    """
    Obtém informações básicas do grupo.

    Returns:
        dict: Informações do grupo ou dicionário vazio em caso de erro
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        chat_info = await bot.get_chat(TELEGRAM_GROUP_ID)

        return {
            'title': chat_info.title,
            'member_count': chat_info.get_member_count(),
            'type': chat_info.type,
            'description': getattr(chat_info, 'description', '')
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações do grupo: {e}")
        return {}

async def get_group_administrators() -> list:
    """
    Obtém lista de administradores do grupo.

    Returns:
        list: Lista de administradores com seus IDs e informações
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            administrators = await bot.get_chat_administrators(TELEGRAM_GROUP_ID)

            admin_list = []
            for admin in administrators:
                # Pula bots (exceto se for o próprio bot do sistema)
                if admin.user.is_bot:
                    continue

                admin_info = {
                    'user_id': admin.user.id,
                    'username': admin.user.username,
                    'first_name': admin.user.first_name,
                    'status': admin.status,  # 'creator' ou 'administrator'
                    'can_be_edited': getattr(admin, 'can_be_edited', False)
                }
                admin_list.append(admin_info)

            logger.info(f"Encontrados {len(admin_list)} administradores no grupo")
            return admin_list

    except Exception as e:
        logger.error(f"Erro ao buscar administradores do grupo: {e}")
        return []

async def send_private_message(user_id: int, message: str) -> bool:
    """
    Envia mensagem privada para um usuário.

    Args:
        user_id: ID do usuário no Telegram
        message: Mensagem a ser enviada

    Returns:
        bool: True se enviou com sucesso, False caso contrário
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            logger.info(f"Mensagem privada enviada para usuário {user_id}")
            return True

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem privada para {user_id}: {e}")
        return False

async def notify_administrators(removed_users: list) -> bool:
    """
    Notifica administradores sobre usuários removidos.

    Args:
        removed_users: Lista de usuários que foram removidos

    Returns:
        bool: True se notificou pelo menos um admin
    """
    if not removed_users:
        logger.info("Nenhum usuário removido - não enviando notificações")
        return True

    try:
        # Busca administradores
        administrators = await get_group_administrators()
        if not administrators:
            logger.warning("Nenhum administrador encontrado para notificar")
            return False

        # Monta a mensagem
        message = "🚨 <b>RELATÓRIO DE CHECKUP DIÁRIO - SENTINELA</b> 🚨\n\n"
        message += f"📅 <b>Data:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
        message += f"🚫 <b>USUÁRIOS REMOVIDOS:</b> {len(removed_users)}\n\n"

        for i, user in enumerate(removed_users, 1):
            message += f"{i}. <b>{user.get('client_name', 'Nome não disponível')}</b>\n"
            message += f"   • ID: {user.get('user_id', 'N/A')}\n"
            message += f"   • CPF: {user.get('cpf', 'N/A')[:3]}***\n"
            message += f"   • Motivo: Contrato inativo\n\n"

        message += "✅ <b>Remoção automática concluída com sucesso!</b>\n\n"
        message += "🔧 <i>Sistema Sentinela - OnCabo</i>"

        # Envia para todos os administradores
        success_count = 0
        for admin in administrators:
            if await send_private_message(admin['user_id'], message):
                success_count += 1
                logger.info(f"Notificação enviada para admin {admin.get('username', admin['user_id'])}")
            else:
                logger.warning(f"Falha ao notificar admin {admin.get('username', admin['user_id'])}")

        logger.info(f"Notificações enviadas para {success_count}/{len(administrators)} administradores")
        return success_count > 0

    except Exception as e:
        logger.error(f"Erro ao notificar administradores: {e}")
        return False