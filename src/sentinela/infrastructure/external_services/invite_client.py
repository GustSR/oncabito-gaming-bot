"""
Cliente para criação de convites do Telegram.
"""

from abc import ABC, abstractmethod
from typing import Optional


class InviteClient(ABC):
    """
    Interface abstrata para criação de convites.
    """

    @abstractmethod
    async def create_temporary_invite_link(self, user_id: int, username: str) -> Optional[str]:
        """
        Cria link temporário de convite para o grupo.

        Args:
            user_id: ID do usuário no Telegram
            username: Username do usuário

        Returns:
            Link de convite ou None se erro
        """
        pass