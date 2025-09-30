"""
Support Conversation Repository Interface.

Define o contrato para persistência de conversas de suporte.
"""

from abc import abstractmethod
from typing import List, Optional
from datetime import datetime

from .base import Repository
from ..entities.support_conversation import SupportConversation, ConversationState
from ..value_objects.identifiers import ConversationId, UserId


class SupportConversationRepository(Repository[SupportConversation, ConversationId]):
    """
    Interface para persistência de conversas de suporte.

    Define operações específicas para a entidade SupportConversation.
    """

    @abstractmethod
    async def find_active_by_user(self, user_id: UserId) -> Optional[SupportConversation]:
        """
        Busca conversa ativa de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Optional[SupportConversation]: Conversa ativa ou None
        """
        pass

    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> List[SupportConversation]:
        """
        Busca todas as conversas de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            List[SupportConversation]: Lista de conversas do usuário
        """
        pass

    @abstractmethod
    async def find_by_state(self, state: ConversationState) -> List[SupportConversation]:
        """
        Busca conversas por estado.

        Args:
            state: Estado das conversas

        Returns:
            List[SupportConversation]: Lista de conversas no estado
        """
        pass

    @abstractmethod
    async def find_expired_conversations(
        self,
        timeout_minutes: int = 30
    ) -> List[SupportConversation]:
        """
        Busca conversas expiradas (sem atividade há muito tempo).

        Args:
            timeout_minutes: Minutos de timeout

        Returns:
            List[SupportConversation]: Lista de conversas expiradas
        """
        pass

    @abstractmethod
    async def count_active_conversations(self) -> int:
        """
        Conta conversas ativas no sistema.

        Returns:
            int: Número de conversas ativas
        """
        pass

    @abstractmethod
    async def count_conversations_by_user(self, user_id: UserId) -> int:
        """
        Conta conversas de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            int: Número de conversas do usuário
        """
        pass

    @abstractmethod
    async def deactivate_user_conversations(self, user_id: UserId) -> int:
        """
        Desativa todas as conversas ativas de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            int: Número de conversas desativadas
        """
        pass

    @abstractmethod
    async def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """
        Remove conversas antigas finalizadas.

        Args:
            days_old: Dias de idade para remoção

        Returns:
            int: Número de conversas removidas
        """
        pass

    @abstractmethod
    async def get_conversation_statistics(self) -> dict:
        """
        Obtém estatísticas das conversas.

        Returns:
            dict: Estatísticas das conversas
        """
        pass