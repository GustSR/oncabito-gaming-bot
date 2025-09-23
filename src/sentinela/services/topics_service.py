import logging
from datetime import datetime
from telegram import Bot, Update
from telegram.error import TelegramError
from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID
from src.sentinela.clients.db_client import get_db_connection

logger = logging.getLogger(__name__)

class TopicsService:
    """Serviço para gerenciar e identificar tópicos do grupo."""

    def __init__(self):
        self.bot = Bot(token=TELEGRAM_TOKEN)
        self.topics_cache = {}
        self.last_update = None

    async def discover_topics_from_messages(self, update: Update) -> dict:
        """
        Descobre tópicos através de mensagens recebidas.

        Args:
            update: Update do Telegram

        Returns:
            dict: Informações do tópico descoberto
        """
        try:
            message = update.message
            if not message or str(message.chat.id) != str(TELEGRAM_GROUP_ID):
                return {}

            # Verifica se a mensagem tem thread_id (é de um tópico)
            thread_id = getattr(message, 'message_thread_id', None)
            if not thread_id:
                return {}

            # Tenta obter informações do tópico
            topic_info = await self.get_topic_info(thread_id, message)

            if topic_info:
                # Salva no cache e banco
                await self.save_topic_info(topic_info)
                logger.info(f"Tópico descoberto: {topic_info['name']} (ID: {topic_info['id']})")

            return topic_info

        except Exception as e:
            logger.error(f"Erro ao descobrir tópico: {e}")
            return {}

    async def get_topic_info(self, thread_id: int, message) -> dict:
        """
        Obtém informações detalhadas de um tópico.

        Args:
            thread_id: ID do tópico
            message: Mensagem do tópico

        Returns:
            dict: Informações do tópico
        """
        try:
            # Informações básicas do tópico
            topic_info = {
                'id': thread_id,
                'name': 'Tópico Desconhecido',
                'discovered_at': datetime.now(),
                'last_message_id': message.message_id,
                'last_activity': datetime.now()
            }

            # Tenta descobrir o nome através da mensagem reply_to_message
            if message.reply_to_message and message.reply_to_message.forum_topic_created:
                topic_info['name'] = message.reply_to_message.forum_topic_created.name
            elif message.reply_to_message and hasattr(message.reply_to_message, 'forum_topic_edited'):
                topic_info['name'] = message.reply_to_message.forum_topic_edited.name

            # Se não conseguiu descobrir o nome, usa uma estratégia alternativa
            if topic_info['name'] == 'Tópico Desconhecido':
                topic_info['name'] = await self.guess_topic_name(thread_id, message)

            return topic_info

        except Exception as e:
            logger.error(f"Erro ao obter info do tópico {thread_id}: {e}")
            return {}

    async def guess_topic_name(self, thread_id: int, message) -> str:
        """
        Tenta adivinhar o nome do tópico baseado no contexto.

        Args:
            thread_id: ID do tópico
            message: Mensagem do tópico

        Returns:
            str: Nome estimado do tópico
        """
        try:
            # Estratégias para descobrir nome do tópico
            text = message.text or message.caption or ""

            # Verifica palavras-chave comuns
            if any(word in text.lower() for word in ['regra', 'rule', 'norma']):
                return "📋 Regras"
            elif any(word in text.lower() for word in ['bem-vindo', 'welcome', 'boas-vindas']):
                return "👋 Boas-vindas"
            elif any(word in text.lower() for word in ['anúncio', 'announcement', 'aviso']):
                return "📢 Anúncios"
            elif any(word in text.lower() for word in ['suporte', 'support', 'ajuda', 'help']):
                return "🆘 Suporte"
            elif any(word in text.lower() for word in ['game', 'jogo', 'gaming']):
                return "🎮 Gaming"
            elif any(word in text.lower() for word in ['geral', 'general', 'chat']):
                return "💬 Chat Geral"
            else:
                return f"Tópico {thread_id}"

        except Exception as e:
            logger.error(f"Erro ao adivinhar nome do tópico: {e}")
            return f"Tópico {thread_id}"

    async def save_topic_info(self, topic_info: dict) -> bool:
        """
        Salva informações do tópico no banco de dados.

        Args:
            topic_info: Informações do tópico

        Returns:
            bool: True se salvou com sucesso
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Cria tabela se não existir
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS group_topics (
                        topic_id INTEGER PRIMARY KEY,
                        topic_name TEXT NOT NULL,
                        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message_id INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insere ou atualiza tópico
                cursor.execute("""
                    INSERT OR REPLACE INTO group_topics
                    (topic_id, topic_name, last_activity, last_message_id, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    topic_info['id'],
                    topic_info['name'],
                    topic_info['last_activity'],
                    topic_info['last_message_id']
                ))

                conn.commit()

            # Atualiza cache
            self.topics_cache[topic_info['id']] = topic_info
            logger.info(f"Tópico salvo: {topic_info['name']} (ID: {topic_info['id']})")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar tópico: {e}")
            return False

    async def get_all_topics(self) -> list:
        """
        Retorna todos os tópicos descobertos.

        Returns:
            list: Lista de tópicos
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT topic_id, topic_name, discovered_at, last_activity, last_message_id
                    FROM group_topics
                    WHERE is_active = 1
                    ORDER BY last_activity DESC
                """)
                results = cursor.fetchall()

                topics = []
                for row in results:
                    topics.append({
                        'id': row[0],
                        'name': row[1],
                        'discovered_at': row[2],
                        'last_activity': row[3],
                        'last_message_id': row[4]
                    })

                return topics

        except Exception as e:
            logger.error(f"Erro ao buscar tópicos: {e}")
            return []

    async def format_topics_list(self) -> str:
        """
        Formata lista de tópicos para exibição.

        Returns:
            str: Lista formatada dos tópicos
        """
        try:
            topics = await self.get_all_topics()

            if not topics:
                return "❌ Nenhum tópico descoberto ainda.\n\n💡 Envie mensagens nos tópicos para que eu possa identificá-los!"

            message = "📋 <b>TÓPICOS DESCOBERTOS NO GRUPO</b>\n\n"
            message += f"🏠 <b>Grupo:</b> {TELEGRAM_GROUP_ID}\n"
            message += f"📊 <b>Total:</b> {len(topics)} tópicos\n\n"

            for i, topic in enumerate(topics, 1):
                message += f"{i}. <b>{topic['name']}</b>\n"
                message += f"   🆔 <code>ID: {topic['id']}</code>\n"
                message += f"   📅 Descoberto: {topic['discovered_at'][:19]}\n"
                message += f"   🕒 Última atividade: {topic['last_activity'][:19]}\n\n"

            message += "🔧 <b>Para configurar:</b>\n"
            message += "• Copie o ID do tópico desejado\n"
            message += "• Adicione no arquivo .env:\n"
            message += f"• <code>RULES_TOPIC_ID=\"ID_AQUI\"</code>\n"
            message += f"• <code>WELCOME_TOPIC_ID=\"ID_AQUI\"</code>\n\n"
            message += "🔄 <b>Use /topics para atualizar esta lista</b>"

            return message

        except Exception as e:
            logger.error(f"Erro ao formatar lista de tópicos: {e}")
            return "❌ Erro ao carregar lista de tópicos."

    async def get_topic_suggestions(self) -> dict:
        """
        Sugere configurações baseadas nos tópicos descobertos.

        Returns:
            dict: Sugestões de configuração
        """
        try:
            topics = await self.get_all_topics()
            suggestions = {
                'rules_topic': None,
                'welcome_topic': None,
                'other_topics': []
            }

            for topic in topics:
                name_lower = topic['name'].lower()

                # Sugere tópico de regras
                if any(word in name_lower for word in ['regra', 'rule', 'norma']) and not suggestions['rules_topic']:
                    suggestions['rules_topic'] = topic

                # Sugere tópico de boas-vindas
                elif any(word in name_lower for word in ['bem-vindo', 'welcome', 'boas-vindas']) and not suggestions['welcome_topic']:
                    suggestions['welcome_topic'] = topic

                # Outros tópicos
                else:
                    suggestions['other_topics'].append(topic)

            return suggestions

        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {e}")
            return {'rules_topic': None, 'welcome_topic': None, 'other_topics': []}

    async def auto_configure_topics(self) -> str:
        """
        Gera configurações automáticas baseadas nos tópicos descobertos.

        Returns:
            str: Configurações sugeridas
        """
        try:
            suggestions = await self.get_topic_suggestions()

            message = "🔧 <b>CONFIGURAÇÃO AUTOMÁTICA SUGERIDA</b>\n\n"

            if suggestions['rules_topic']:
                topic = suggestions['rules_topic']
                message += f"📋 <b>Tópico de Regras:</b>\n"
                message += f"   • Nome: {topic['name']}\n"
                message += f"   • ID: <code>{topic['id']}</code>\n"
                message += f"   • Configuração: <code>RULES_TOPIC_ID=\"{topic['id']}\"</code>\n\n"
            else:
                message += "📋 <b>Tópico de Regras:</b> ❌ Não encontrado\n"
                message += "   💡 Crie um tópico com 'regras' no nome\n\n"

            if suggestions['welcome_topic']:
                topic = suggestions['welcome_topic']
                message += f"👋 <b>Tópico de Boas-vindas:</b>\n"
                message += f"   • Nome: {topic['name']}\n"
                message += f"   • ID: <code>{topic['id']}</code>\n"
                message += f"   • Configuração: <code>WELCOME_TOPIC_ID=\"{topic['id']}\"</code>\n\n"
            else:
                message += "👋 <b>Tópico de Boas-vindas:</b> ❌ Não encontrado\n"
                message += "   💡 Crie um tópico com 'boas-vindas' no nome\n\n"

            if suggestions['other_topics']:
                message += f"📂 <b>Outros Tópicos ({len(suggestions['other_topics'])}):</b>\n"
                for topic in suggestions['other_topics'][:3]:  # Mostra só os 3 primeiros
                    message += f"   • {topic['name']} (ID: {topic['id']})\n"
                if len(suggestions['other_topics']) > 3:
                    message += f"   • ... e mais {len(suggestions['other_topics']) - 3}\n"
                message += "\n"

            message += "💾 <b>Para aplicar as configurações:</b>\n"
            message += "1. Copie os IDs sugeridos\n"
            message += "2. Adicione no arquivo .env\n"
            message += "3. Reinicie o bot\n"
            message += "4. Use /test_topics para validar"

            return message

        except Exception as e:
            logger.error(f"Erro na configuração automática: {e}")
            return "❌ Erro ao gerar configuração automática."

# Instância global do serviço
topics_service = TopicsService()