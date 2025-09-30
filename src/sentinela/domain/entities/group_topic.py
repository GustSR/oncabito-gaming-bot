"""
Group Topic Entity.

Representa um tópico do grupo do Telegram.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from .base import Entity
from ..value_objects.identifiers import UserId


class TopicCategory(Enum):
    """Categoria de tópico."""

    RULES = "rules"              # Regras da comunidade
    WELCOME = "welcome"          # Boas-vindas
    ANNOUNCEMENTS = "announcements"  # Anúncios
    SUPPORT = "support"          # Suporte/Ajuda
    GAMING = "gaming"            # Gaming geral
    GAME_SPECIFIC = "game_specific"  # Jogo específico
    GENERAL = "general"          # Chat geral
    UNKNOWN = "unknown"          # Desconhecido


@dataclass
class GroupTopic(Entity):
    """
    Representa um tópico do grupo Telegram.

    Attributes:
        topic_id: ID do tópico no Telegram
        name: Nome do tópico
        category: Categoria do tópico
        is_active: Se o tópico está ativo
        discovered_at: Data de descoberta
        last_activity: Última atividade registrada
        last_message_id: ID da última mensagem
        message_count: Contador de mensagens
        icon_emoji: Emoji do ícone (se disponível)
    """

    topic_id: int
    name: str
    category: TopicCategory = TopicCategory.UNKNOWN
    is_active: bool = True
    discovered_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_message_id: Optional[int] = None
    message_count: int = 0
    icon_emoji: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_activity(self, message_id: int) -> None:
        """
        Atualiza última atividade do tópico.

        Args:
            message_id: ID da mensagem recebida
        """
        self.last_activity = datetime.now()
        self.last_message_id = message_id
        self.message_count += 1
        self.updated_at = datetime.now()

    def mark_inactive(self) -> None:
        """Marca tópico como inativo."""
        self.is_active = False
        self.updated_at = datetime.now()

    def mark_active(self) -> None:
        """Marca tópico como ativo."""
        self.is_active = True
        self.updated_at = datetime.now()

    def update_name(self, new_name: str) -> None:
        """
        Atualiza nome do tópico.

        Args:
            new_name: Novo nome
        """
        self.name = new_name
        self.updated_at = datetime.now()

        # Tenta re-categorizar baseado no novo nome
        self.category = self._guess_category_from_name(new_name)

    def get_display_name(self) -> str:
        """
        Retorna nome para exibição.

        Returns:
            str: Nome formatado com emoji
        """
        if self.icon_emoji:
            return f"{self.icon_emoji} {self.name}"
        return self.name

    def is_rules_topic(self) -> bool:
        """Verifica se é tópico de regras."""
        return self.category == TopicCategory.RULES

    def is_welcome_topic(self) -> bool:
        """Verifica se é tópico de boas-vindas."""
        return self.category == TopicCategory.WELCOME

    def is_support_topic(self) -> bool:
        """Verifica se é tópico de suporte."""
        return self.category == TopicCategory.SUPPORT

    def is_gaming_topic(self) -> bool:
        """Verifica se é tópico gaming."""
        return self.category in [TopicCategory.GAMING, TopicCategory.GAME_SPECIFIC]

    @staticmethod
    def _guess_category_from_name(name: str) -> TopicCategory:
        """
        Tenta categorizar tópico baseado no nome.

        Args:
            name: Nome do tópico

        Returns:
            TopicCategory: Categoria identificada
        """
        name_lower = name.lower()

        # Mapeia palavras-chave para categorias
        category_keywords = {
            TopicCategory.RULES: ['regra', 'rule', 'norma', 'regulamento'],
            TopicCategory.WELCOME: ['bem-vindo', 'welcome', 'boas-vindas'],
            TopicCategory.ANNOUNCEMENTS: ['anúncio', 'announcement', 'aviso', 'notícia'],
            TopicCategory.SUPPORT: ['suporte', 'support', 'ajuda', 'help', 'técnico'],
            TopicCategory.GAMING: ['game', 'jogo', 'gaming', 'gamer'],
            TopicCategory.GENERAL: ['geral', 'general', 'chat', 'conversa']
        }

        # Verifica cada categoria
        for category, keywords in category_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return category

        return TopicCategory.UNKNOWN

    @staticmethod
    def create_from_message(
        topic_id: int,
        name: str,
        message_id: int,
        icon_emoji: Optional[str] = None
    ) -> 'GroupTopic':
        """
        Cria tópico a partir de mensagem descoberta.

        Args:
            topic_id: ID do tópico
            name: Nome do tópico
            message_id: ID da mensagem
            icon_emoji: Emoji do ícone (opcional)

        Returns:
            GroupTopic: Nova entidade criada
        """
        # Cria entidade com ID único
        entity_id = UserId(topic_id)

        # Determina categoria
        category = GroupTopic._guess_category_from_name(name)

        return GroupTopic(
            id=entity_id,
            topic_id=topic_id,
            name=name,
            category=category,
            last_message_id=message_id,
            message_count=1,
            icon_emoji=icon_emoji
        )

    def to_dict(self) -> dict:
        """Converte entidade para dicionário."""
        return {
            'id': self.id.value,
            'topic_id': self.topic_id,
            'name': self.name,
            'category': self.category.value,
            'is_active': self.is_active,
            'discovered_at': self.discovered_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'last_message_id': self.last_message_id,
            'message_count': self.message_count,
            'icon_emoji': self.icon_emoji,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def get_config_suggestion(self) -> Optional[str]:
        """
        Retorna sugestão de configuração .env.

        Returns:
            Optional[str]: Linha de configuração ou None
        """
        if self.is_rules_topic():
            return f'RULES_TOPIC_ID="{self.topic_id}"'
        elif self.is_welcome_topic():
            return f'WELCOME_TOPIC_ID="{self.topic_id}"'
        return None
