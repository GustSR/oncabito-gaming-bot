import logging
from telegram import Bot
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

logger = logging.getLogger(__name__)

async def scan_group_for_topics() -> list:
    """
    Força a descoberta de tópicos consultando mensagens recentes do grupo.

    Returns:
        list: Lista de tópicos encontrados
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        discovered_topics = {}

        async with bot:
            # Pega as últimas 100 mensagens do grupo
            updates = await bot.get_updates(limit=100)

            for update in updates:
                if update.message:
                    message = update.message

                    # Verifica se é do grupo correto
                    if str(message.chat.id) != str(TELEGRAM_GROUP_ID):
                        continue

                    # Verifica se tem thread_id (é de um tópico)
                    thread_id = getattr(message, 'message_thread_id', None)
                    if thread_id:
                        topic_name = f"Tópico {thread_id}"

                        # Tenta descobrir nome baseado no texto
                        text = message.text or message.caption or ""
                        if text:
                            text_lower = text.lower()
                            if any(word in text_lower for word in ['regra', 'rule', 'norma']):
                                topic_name = "📋 Regras"
                            elif any(word in text_lower for word in ['bem-vindo', 'welcome', 'boas-vindas']):
                                topic_name = "👋 Boas-vindas"
                            elif any(word in text_lower for word in ['anúncio', 'announcement']):
                                topic_name = "📢 Anúncios"
                            elif any(word in text_lower for word in ['suporte', 'support', 'ajuda']):
                                topic_name = "🆘 Suporte"

                        discovered_topics[thread_id] = {
                            'id': thread_id,
                            'name': topic_name,
                            'last_message': message.text[:50] if message.text else ""
                        }

        topics_list = list(discovered_topics.values())
        logger.info(f"Descobertos {len(topics_list)} tópicos via scan direto")

        return topics_list

    except Exception as e:
        logger.error(f"Erro ao escanear grupo para tópicos: {e}")
        return []

async def get_group_real_info() -> dict:
    """
    Obtém informações reais do grupo via API.

    Returns:
        dict: Informações do grupo
    """
    try:
        bot = Bot(token=TELEGRAM_TOKEN)

        async with bot:
            chat_info = await bot.get_chat(TELEGRAM_GROUP_ID)

            return {
                'id': chat_info.id,
                'title': chat_info.title,
                'type': chat_info.type,
                'member_count': chat_info.get_member_count() if hasattr(chat_info, 'get_member_count') else 'N/A',
                'has_topics': chat_info.type == 'supergroup'  # Supergrupos podem ter tópicos
            }

    except Exception as e:
        logger.error(f"Erro ao obter info do grupo: {e}")
        return {}