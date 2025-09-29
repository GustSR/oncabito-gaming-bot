"""
Cliente para operações relacionadas a grupos do Telegram.
"""

from abc import ABC, abstractmethod


class GroupClient(ABC):
    """
    Interface abstrata para operações com grupos.
    """

    @abstractmethod
    async def is_user_in_group(self, user_id: int) -> bool:
        """
        Verifica se usuário está no grupo.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            True se usuário está no grupo, False caso contrário
        """
        pass

    @abstractmethod
    async def remove_user_from_group(self, user_id: int) -> bool:
        """
        Remove usuário do grupo.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            True se removeu com sucesso, False caso contrário
        """
        pass