"""
Topic Management Use Case.

Gerencia descoberta, identificação e configuração
de tópicos do grupo Telegram.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.entities.group_topic import GroupTopic, TopicCategory
from ...domain.repositories.group_topic_repository import GroupTopicRepository
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class TopicDiscoveryResult:
    """Resultado de descoberta de tópico."""

    success: bool
    message: str
    topic: Optional[GroupTopic] = None
    is_new: bool = False


@dataclass
class TopicListResult:
    """Resultado de listagem de tópicos."""

    success: bool
    message: str
    topics: List[GroupTopic] = None
    formatted_text: Optional[str] = None


@dataclass
class TopicSuggestionsResult:
    """Resultado de sugestões de configuração."""

    success: bool
    message: str
    rules_topic: Optional[GroupTopic] = None
    welcome_topic: Optional[GroupTopic] = None
    support_topics: List[GroupTopic] = None
    other_topics: List[GroupTopic] = None
    config_lines: List[str] = None


class TopicManagementUseCase(UseCase):
    """
    Use Case para gerenciamento de tópicos.

    Coordena descoberta automática, identificação e
    sugestões de configuração de tópicos do grupo.
    """

    def __init__(
        self,
        topic_repository: GroupTopicRepository,
        event_bus: EventBus,
        group_id: int
    ):
        """
        Inicializa o use case.

        Args:
            topic_repository: Repositório de tópicos
            event_bus: Event bus para publicar eventos
            group_id: ID do grupo no Telegram
        """
        self.topic_repository = topic_repository
        self.event_bus = event_bus
        self.group_id = group_id

    async def discover_topic_from_message(
        self,
        topic_id: int,
        message_id: int,
        message_text: Optional[str] = None,
        topic_name: Optional[str] = None,
        icon_emoji: Optional[str] = None
    ) -> TopicDiscoveryResult:
        """
        Descobre ou atualiza tópico a partir de mensagem.

        Args:
            topic_id: ID do tópico no Telegram
            message_id: ID da mensagem
            message_text: Texto da mensagem (para heurística)
            topic_name: Nome do tópico (se disponível)
            icon_emoji: Emoji do ícone (se disponível)

        Returns:
            TopicDiscoveryResult: Resultado da descoberta
        """
        try:
            logger.info(f"Descobrindo tópico {topic_id} via mensagem {message_id}")

            # Verifica se tópico já existe
            existing_topic = await self.topic_repository.find_by_topic_id(topic_id)

            if existing_topic:
                # Atualiza atividade
                existing_topic.update_activity(message_id)
                await self.topic_repository.save(existing_topic)

                logger.info(f"Atividade atualizada para tópico {topic_id}")

                return TopicDiscoveryResult(
                    success=True,
                    message="Atividade de tópico atualizada",
                    topic=existing_topic,
                    is_new=False
                )

            # Determina nome do tópico
            if not topic_name:
                topic_name = self._guess_topic_name(topic_id, message_text)

            # Cria novo tópico
            new_topic = GroupTopic.create_from_message(
                topic_id=topic_id,
                name=topic_name,
                message_id=message_id,
                icon_emoji=icon_emoji
            )

            # Salva no repositório
            saved_topic = await self.topic_repository.save(new_topic)

            # Publica evento
            from ...domain.events.group_events import TopicDiscoveredEvent

            await self.event_bus.publish(
                TopicDiscoveredEvent(
                    aggregate_id=str(topic_id),
                    topic_id=topic_id,
                    topic_name=topic_name,
                    category=new_topic.category.value,
                    discovered_at=datetime.now()
                )
            )

            logger.info(f"Novo tópico descoberto: {topic_name} (ID: {topic_id})")

            return TopicDiscoveryResult(
                success=True,
                message=f"Novo tópico descoberto: {topic_name}",
                topic=saved_topic,
                is_new=True
            )

        except Exception as e:
            logger.error(f"Erro ao descobrir tópico {topic_id}: {e}")
            return TopicDiscoveryResult(
                success=False,
                message=f"Erro ao descobrir tópico: {str(e)}"
            )

    async def get_all_topics(
        self,
        active_only: bool = True
    ) -> TopicListResult:
        """
        Lista todos os tópicos descobertos.

        Args:
            active_only: Se deve retornar apenas tópicos ativos

        Returns:
            TopicListResult: Resultado com lista de tópicos
        """
        try:
            logger.info(f"Listando tópicos (active_only={active_only})")

            # Busca tópicos
            if active_only:
                topics = await self.topic_repository.find_all_active()
            else:
                topics = await self.topic_repository.find_all()

            if not topics:
                return TopicListResult(
                    success=True,
                    message="Nenhum tópico descoberto ainda",
                    topics=[],
                    formatted_text=self._format_no_topics_message()
                )

            # Formata mensagem
            formatted_text = self._format_topics_list(topics)

            logger.info(f"Listados {len(topics)} tópicos")

            return TopicListResult(
                success=True,
                message=f"Encontrados {len(topics)} tópicos",
                topics=topics,
                formatted_text=formatted_text
            )

        except Exception as e:
            logger.error(f"Erro ao listar tópicos: {e}")
            return TopicListResult(
                success=False,
                message=f"Erro ao listar tópicos: {str(e)}",
                topics=[]
            )

    async def get_configuration_suggestions(self) -> TopicSuggestionsResult:
        """
        Gera sugestões de configuração baseadas nos tópicos descobertos.

        Returns:
            TopicSuggestionsResult: Sugestões de configuração
        """
        try:
            logger.info("Gerando sugestões de configuração de tópicos")

            # Busca tópicos categorizados
            rules_topic = await self.topic_repository.find_rules_topic()
            welcome_topic = await self.topic_repository.find_welcome_topic()
            support_topics = await self.topic_repository.find_support_topics()

            # Busca outros tópicos
            all_topics = await self.topic_repository.find_all_active()
            other_topics = [
                t for t in all_topics
                if t.category not in [
                    TopicCategory.RULES,
                    TopicCategory.WELCOME,
                    TopicCategory.SUPPORT
                ]
            ]

            # Gera linhas de configuração
            config_lines = []
            if rules_topic:
                config_lines.append(f'RULES_TOPIC_ID="{rules_topic.topic_id}"')
            if welcome_topic:
                config_lines.append(f'WELCOME_TOPIC_ID="{welcome_topic.topic_id}"')

            # Formata mensagem
            formatted_message = self._format_suggestions(
                rules_topic,
                welcome_topic,
                support_topics,
                other_topics,
                config_lines
            )

            logger.info("Sugestões de configuração geradas")

            return TopicSuggestionsResult(
                success=True,
                message=formatted_message,
                rules_topic=rules_topic,
                welcome_topic=welcome_topic,
                support_topics=support_topics or [],
                other_topics=other_topics,
                config_lines=config_lines
            )

        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {e}")
            return TopicSuggestionsResult(
                success=False,
                message=f"Erro ao gerar sugestões: {str(e)}",
                support_topics=[],
                other_topics=[],
                config_lines=[]
            )

    async def update_topic_name(
        self,
        topic_id: int,
        new_name: str
    ) -> UseCaseResult:
        """
        Atualiza nome de um tópico.

        Args:
            topic_id: ID do tópico
            new_name: Novo nome

        Returns:
            UseCaseResult: Resultado da atualização
        """
        try:
            logger.info(f"Atualizando nome do tópico {topic_id} para '{new_name}'")

            topic = await self.topic_repository.find_by_topic_id(topic_id)

            if not topic:
                return UseCaseResult(
                    success=False,
                    message="Tópico não encontrado"
                )

            old_name = topic.name
            topic.update_name(new_name)
            await self.topic_repository.save(topic)

            logger.info(f"Nome do tópico {topic_id} atualizado: '{old_name}' → '{new_name}'")

            return UseCaseResult(
                success=True,
                message=f"Nome atualizado: '{old_name}' → '{new_name}'",
                data={'topic_id': topic_id, 'new_name': new_name}
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar nome do tópico {topic_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao atualizar nome: {str(e)}"
            )

    async def mark_topic_inactive(self, topic_id: int) -> UseCaseResult:
        """
        Marca tópico como inativo.

        Args:
            topic_id: ID do tópico

        Returns:
            UseCaseResult: Resultado da operação
        """
        try:
            topic = await self.topic_repository.find_by_topic_id(topic_id)

            if not topic:
                return UseCaseResult(
                    success=False,
                    message="Tópico não encontrado"
                )

            topic.mark_inactive()
            await self.topic_repository.save(topic)

            logger.info(f"Tópico {topic_id} marcado como inativo")

            return UseCaseResult(
                success=True,
                message="Tópico marcado como inativo"
            )

        except Exception as e:
            logger.error(f"Erro ao marcar tópico {topic_id} como inativo: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro: {str(e)}"
            )

    # Private helper methods

    def _guess_topic_name(
        self,
        topic_id: int,
        message_text: Optional[str]
    ) -> str:
        """
        Tenta adivinhar nome do tópico baseado em heurística.

        Args:
            topic_id: ID do tópico
            message_text: Texto da mensagem

        Returns:
            str: Nome estimado
        """
        if not message_text:
            return f"Tópico {topic_id}"

        text_lower = message_text.lower()

        # Mapeamento de palavras-chave
        keyword_map = {
            ('regra', 'rule', 'norma'): "📋 Regras",
            ('bem-vindo', 'welcome', 'boas-vindas'): "👋 Boas-vindas",
            ('anúncio', 'announcement', 'aviso'): "📢 Anúncios",
            ('suporte', 'support', 'ajuda', 'help'): "🆘 Suporte",
            ('game', 'jogo', 'gaming'): "🎮 Gaming",
            ('geral', 'general', 'chat'): "💬 Chat Geral"
        }

        for keywords, name in keyword_map.items():
            if any(keyword in text_lower for keyword in keywords):
                return name

        return f"Tópico {topic_id}"

    def _format_no_topics_message(self) -> str:
        """Formata mensagem quando não há tópicos."""
        return (
            "❌ Nenhum tópico descoberto ainda.\n\n"
            "💡 Envie mensagens nos tópicos para que eu possa identificá-los!"
        )

    def _format_topics_list(self, topics: List[GroupTopic]) -> str:
        """
        Formata lista de tópicos para exibição.

        Args:
            topics: Lista de tópicos

        Returns:
            str: Mensagem formatada
        """
        message = "📋 <b>TÓPICOS DESCOBERTOS NO GRUPO</b>\n\n"
        message += f"🏠 <b>Grupo ID:</b> {self.group_id}\n"
        message += f"📊 <b>Total:</b> {len(topics)} tópicos\n\n"

        for i, topic in enumerate(topics, 1):
            message += f"{i}. <b>{topic.get_display_name()}</b>\n"
            message += f"   🆔 <code>ID: {topic.topic_id}</code>\n"
            message += f"   📂 Categoria: {topic.category.value}\n"
            message += f"   📅 Descoberto: {topic.discovered_at.strftime('%d/%m/%Y %H:%M')}\n"
            message += f"   📊 Mensagens: {topic.message_count}\n"
            message += f"   🕒 Última atividade: {topic.last_activity.strftime('%d/%m/%Y %H:%M')}\n\n"

        message += "🔧 <b>Para configurar:</b>\n"
        message += "• Copie o ID do tópico desejado\n"
        message += "• Adicione no arquivo .env\n"
        message += "• Use /topics_config para ver sugestões\n\n"
        message += "🔄 <b>Use /topics para atualizar esta lista</b>"

        return message

    def _format_suggestions(
        self,
        rules_topic: Optional[GroupTopic],
        welcome_topic: Optional[GroupTopic],
        support_topics: List[GroupTopic],
        other_topics: List[GroupTopic],
        config_lines: List[str]
    ) -> str:
        """Formata mensagem de sugestões."""
        message = "🔧 <b>CONFIGURAÇÃO AUTOMÁTICA SUGERIDA</b>\n\n"

        # Tópico de regras
        if rules_topic:
            message += f"📋 <b>Tópico de Regras:</b>\n"
            message += f"   • Nome: {rules_topic.get_display_name()}\n"
            message += f"   • ID: <code>{rules_topic.topic_id}</code>\n"
            message += f"   • Config: <code>RULES_TOPIC_ID=\"{rules_topic.topic_id}\"</code>\n\n"
        else:
            message += "📋 <b>Tópico de Regras:</b> ❌ Não encontrado\n"
            message += "   💡 Crie um tópico com 'regras' no nome\n\n"

        # Tópico de boas-vindas
        if welcome_topic:
            message += f"👋 <b>Tópico de Boas-vindas:</b>\n"
            message += f"   • Nome: {welcome_topic.get_display_name()}\n"
            message += f"   • ID: <code>{welcome_topic.topic_id}</code>\n"
            message += f"   • Config: <code>WELCOME_TOPIC_ID=\"{welcome_topic.topic_id}\"</code>\n\n"
        else:
            message += "👋 <b>Tópico de Boas-vindas:</b> ❌ Não encontrado\n"
            message += "   💡 Crie um tópico com 'boas-vindas' no nome\n\n"

        # Tópicos de suporte
        if support_topics:
            message += f"🆘 <b>Tópicos de Suporte ({len(support_topics)}):</b>\n"
            for topic in support_topics[:2]:
                message += f"   • {topic.get_display_name()} (ID: {topic.topic_id})\n"
            if len(support_topics) > 2:
                message += f"   • ... e mais {len(support_topics) - 2}\n"
            message += "\n"

        # Outros tópicos
        if other_topics:
            message += f"📂 <b>Outros Tópicos ({len(other_topics)}):</b>\n"
            for topic in other_topics[:3]:
                message += f"   • {topic.get_display_name()} (ID: {topic.topic_id})\n"
            if len(other_topics) > 3:
                message += f"   • ... e mais {len(other_topics) - 3}\n"
            message += "\n"

        # Configuração final
        if config_lines:
            message += "💾 <b>Adicione no .env:</b>\n"
            for line in config_lines:
                message += f"<code>{line}</code>\n"
            message += "\n"

        message += "🔄 <b>Reinicie o bot após configurar</b>"

        return message
