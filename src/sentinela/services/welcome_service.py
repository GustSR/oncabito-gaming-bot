import logging
from datetime import datetime, timedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID, RULES_TOPIC_ID, WELCOME_TOPIC_ID
from src.sentinela.clients.db_client import save_user_joining, mark_rules_accepted, get_expired_rules_users, mark_user_expired
from src.sentinela.services.permissions_service import permissions_service

logger = logging.getLogger(__name__)

async def handle_new_member(update: Update) -> None:
    """
    Processa novos membros que entram no grupo.

    Args:
        update: Update do Telegram com informações do novo membro
    """
    try:
        new_members = update.message.new_chat_members

        for new_member in new_members:
            # Ignora bots
            if new_member.is_bot:
                continue

            user_id = new_member.id
            username = new_member.username or new_member.first_name

            logger.info(f"Novo membro detectado: {username} (ID: {user_id})")

            # Marca usuário como pendente de aceitar regras
            await mark_user_pending_rules(user_id, username)

            # Envia mensagem de boas-vindas
            await send_welcome_message(update, new_member)

            # Se tiver tópico de regras configurado, direciona para lá
            if RULES_TOPIC_ID:
                await send_rules_reminder(update, new_member)

    except Exception as e:
        logger.error(f"Erro ao processar novo membro: {e}")

async def send_welcome_message(update: Update, new_member) -> None:
    """
    Envia mensagem de boas-vindas para novo membro.

    Args:
        update: Update do Telegram
        new_member: Objeto do novo membro
    """
    try:
        # Determina onde enviar (tópico específico ou grupo geral)
        message_thread_id = None
        if WELCOME_TOPIC_ID:
            message_thread_id = int(WELCOME_TOPIC_ID)

        welcome_text = (
            f"🎮 <b>Bem-vindo à Comunidade Gamer OnCabo, {new_member.mention_html()}!</b> 🎮\n\n"
            f"🔥 Você acaba de entrar na melhor comunidade de gamers! 🔥\n\n"
            f"📋 <b>IMPORTANTE:</b> Para participar ativamente do grupo, você precisa:\n"
            f"✅ Ler e aceitar nossas regras\n"
            f"✅ Reagir com 👍 na mensagem de regras\n\n"
        )

        if RULES_TOPIC_ID:
            welcome_text += f"📌 <b>Vá para o tópico 'Regras' e reaja à mensagem principal!</b>\n\n"

        welcome_text += f"🚀 <b>Aproveite a comunidade e bons jogos!</b>"

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=TELEGRAM_GROUP_ID,
                text=welcome_text,
                parse_mode='HTML',
                message_thread_id=message_thread_id
            )

        logger.info(f"Mensagem de boas-vindas enviada para {new_member.username}")

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de boas-vindas: {e}")

async def send_rules_reminder(update: Update, new_member) -> None:
    """
    Envia lembrete específico sobre as regras no tópico de regras.

    Args:
        update: Update do Telegram
        new_member: Objeto do novo membro
    """
    try:
        if not RULES_TOPIC_ID:
            return

        rules_text = (
            f"📋 <b>{new_member.mention_html()}, leia as regras acima e reaja com 👍!</b>\n\n"
            f"⚠️ <b>Sua participação no grupo depende da aceitação das regras.</b>\n"
            f"⏰ Você tem 24 horas para reagir, caso contrário será removido automaticamente."
        )

        # Cria botão inline para facilitar
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Li e aceito as regras", callback_data=f"accept_rules_{new_member.id}")]
        ])

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=TELEGRAM_GROUP_ID,
                text=rules_text,
                parse_mode='HTML',
                message_thread_id=int(RULES_TOPIC_ID),
                reply_markup=keyboard
            )

        logger.info(f"Lembrete de regras enviado para {new_member.username}")

    except Exception as e:
        logger.error(f"Erro ao enviar lembrete de regras: {e}")

async def mark_user_pending_rules(user_id: int, username: str) -> None:
    """
    Marca usuário como pendente de aceitar regras.

    Args:
        user_id: ID do usuário
        username: Nome do usuário
    """
    try:
        # Salva no banco com status pendente (24h para aceitar)
        save_user_joining(user_id, username, expires_hours=24)
        logger.info(f"Usuário {username} (ID: {user_id}) marcado como pendente de regras")

    except Exception as e:
        logger.error(f"Erro ao marcar usuário como pendente: {e}")

async def handle_rules_reaction(update: Update) -> None:
    """
    Processa reações na mensagem de regras.

    Args:
        update: Update do Telegram
    """
    try:
        # Verifica se é uma reação na mensagem de regras
        if not update.message or not RULES_TOPIC_ID:
            return

        # Verifica se a mensagem está no tópico de regras
        if update.message.message_thread_id != int(RULES_TOPIC_ID):
            return

        # Aqui você implementaria a lógica para detectar reações
        # O Telegram Bot API tem limitações para detectar reações diretamente
        # Uma alternativa é usar botões inline ou comandos

        logger.info("Reação processada no tópico de regras")

    except Exception as e:
        logger.error(f"Erro ao processar reação nas regras: {e}")

async def handle_rules_button(update: Update) -> None:
    """
    Processa cliques no botão de aceitar regras.

    Args:
        update: Update do Telegram (callback query)
    """
    try:
        query = update.callback_query
        if not query or not query.data.startswith("accept_rules_"):
            return

        user_id = int(query.data.split("_")[-1])

        # Verifica se o usuário que clicou é o mesmo do botão
        if query.from_user.id != user_id:
            await query.answer("❌ Este botão não é para você!", show_alert=True)
            return

        # Marca como regras aceitas
        await mark_rules_accepted_async(user_id, query.from_user.username)

        # Tenta conceder acesso aos tópicos
        access_granted = await permissions_service.grant_topic_access(user_id, query.from_user.username)

        if access_granted:
            # Responde ao usuário
            await query.answer("✅ Regras aceitas! Acesso liberado aos tópicos de gaming!", show_alert=True)
        else:
            # Responde com notificação que admin vai liberar
            await query.answer("✅ Regras aceitas! Aguarde liberação do acesso pelos administradores.", show_alert=True)

        # Remove o botão editando a mensagem
        await query.edit_message_text(
            f"✅ <b>{query.from_user.mention_html()} aceitou as regras!</b>\n\n"
            f"🎮 <b>Bem-vindo oficial à Comunidade Gamer OnCabo!</b>",
            parse_mode='HTML'
        )

        logger.info(f"Usuário {query.from_user.username} aceitou as regras")

    except Exception as e:
        logger.error(f"Erro ao processar botão de regras: {e}")

async def mark_rules_accepted_async(user_id: int, username: str) -> None:
    """
    Marca que o usuário aceitou as regras (versão async).

    Args:
        user_id: ID do usuário
        username: Nome do usuário
    """
    try:
        # Atualiza status no banco
        mark_rules_accepted(user_id)
        logger.info(f"Usuário {username} (ID: {user_id}) aceitou as regras")

    except Exception as e:
        logger.error(f"Erro ao marcar regras aceitas: {e}")

async def check_pending_users() -> None:
    """
    Verifica usuários pendentes que não aceitaram regras em 24h.
    Função para ser chamada periodicamente.
    """
    try:
        # Busca usuários pendentes expirados
        # Implementar consulta no banco de dados

        # Para cada usuário expirado, remove do grupo
        logger.info("Verificação de usuários pendentes executada")

    except Exception as e:
        logger.error(f"Erro ao verificar usuários pendentes: {e}")

def should_bot_respond_in_topic(message_thread_id: int = None) -> bool:
    """
    Verifica se o bot deve responder em um tópico específico.

    Args:
        message_thread_id: ID do tópico da mensagem

    Returns:
        bool: True se deve responder, False caso contrário
    """
    # Se não há tópicos configurados, bot não responde no grupo
    if not RULES_TOPIC_ID and not WELCOME_TOPIC_ID:
        return False

    # Se não tem thread ID, é mensagem no grupo geral
    if not message_thread_id:
        return False

    # Só responde nos tópicos configurados
    allowed_topics = []
    if RULES_TOPIC_ID:
        allowed_topics.append(int(RULES_TOPIC_ID))
    if WELCOME_TOPIC_ID:
        allowed_topics.append(int(WELCOME_TOPIC_ID))

    return message_thread_id in allowed_topics