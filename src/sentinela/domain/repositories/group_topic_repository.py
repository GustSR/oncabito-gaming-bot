"""
Group Topic Repository.

Interface abstrata para persistência de tópicos do grupo.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.group_topic import GroupTopic, TopicCategory


class GroupTopicRepository(ABC):
    """
    Repositório abstrato para tópicos do grupo.

    Define operações de persistência para GroupTopic.
    """

    @abstractmethod
    async def save(self, topic: GroupTopic) -> GroupTopic:
        """
        Salva ou atualiza um tópico.

        Args:
            topic: Entidade do tópico

        Returns:
            GroupTopic: Tópico salvo
        """
        pass

    @abstractmethod
    async def find_by_topic_id(self, topic_id: int) -> Optional[GroupTopic]:
        """
        Busca tópico por ID do Telegram.

        Args:
            topic_id: ID do tópico no Telegram

        Returns:
            Optional[GroupTopic]: Tópico encontrado ou None
        """
        pass

    @abstractmethod
    async def find_by_category(self, category: TopicCategory) -> List[GroupTopic]:
        """
        Busca tópicos por categoria.

        Args:
            category: Categoria desejada

        Returns:
            List[GroupTopic]: Lista de tópicos
        """
        pass

    @abstractmethod
    async def find_all_active(self) -> List[GroupTopic]:
        """
        Busca todos os tópicos ativos.

        Returns:
            List[GroupTopic]: Lista de tópicos ativos
        """
        pass

    @abstractmethod
    async def find_all(self) -> List[GroupTopic]:
        """
        Busca todos os tópicos (ativos e inativos).

        Returns:
            List[GroupTopic]: Lista de todos os tópicos
        """
        pass

    @abstractmethod
    async def exists(self, topic_id: int) -> bool:
        """
        Verifica se tópico existe.

        Args:
            topic_id: ID do tópico

        Returns:
            bool: True se existe
        """
        pass

    @abstractmethod
    async def delete(self, topic_id: int) -> bool:
        """
        Remove tópico do repositório.

        Args:
            topic_id: ID do tópico

        Returns:
            bool: True se removeu com sucesso
        """
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """
        Conta tópicos ativos.

        Returns:
            int: Número de tópicos ativos
        """
        pass

    @abstractmethod
    async def find_rules_topic(self) -> Optional[GroupTopic]:
        """
        Busca tópico de regras.

        Returns:
            Optional[GroupTopic]: Tópico de regras ou None
        """
        pass

    @abstractmethod
    async def find_welcome_topic(self) -> Optional[GroupTopic]:
        """
        Busca tópico de boas-vindas.

        Returns:
            Optional[GroupTopic]: Tópico de boas-vindas ou None
        """
        pass

    @abstractmethod
    async def find_support_topics(self) -> List[GroupTopic]:
        """
        Busca tópicos de suporte.

        Returns:
            List[GroupTopic]: Lista de tópicos de suporte
        """
        pass

    @abstractmethod
    async def update_activity(
        self,
        topic_id: int,
        message_id: int
    ) -> bool:
        """
        Atualiza atividade de um tópico.

        Args:
            topic_id: ID do tópico
            message_id: ID da mensagem

        Returns:
            bool: True se atualizou com sucesso
        """
        pass
