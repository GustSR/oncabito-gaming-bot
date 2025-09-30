"""
User Repository Interface.

Define o contrato para persistência de usuários.
"""

from abc import abstractmethod
from typing import List, Optional
from datetime import datetime

from .base import Repository
from ..entities.user import User
from ..value_objects.identifiers import UserId


class UserRepository(Repository[User, UserId]):
    """
    Interface para persistência de usuários.

    Define operações específicas para a entidade User.
    """

    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Busca usuário por ID do Telegram.

        Args:
            telegram_id: ID do usuário no Telegram

        Returns:
            Optional[User]: Usuário encontrado ou None
        """
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        """
        Busca usuário por username.

        Args:
            username: Username do usuário

        Returns:
            Optional[User]: Usuário encontrado ou None
        """
        pass

    @abstractmethod
    async def find_active_users(self) -> List[User]:
        """
        Busca todos os usuários ativos.

        Returns:
            List[User]: Lista de usuários ativos
        """
        pass

    @abstractmethod
    async def find_banned_users(self) -> List[User]:
        """
        Busca usuários banidos.

        Returns:
            List[User]: Lista de usuários banidos
        """
        pass

    @abstractmethod
    async def count_active_users(self) -> int:
        """
        Conta usuários ativos.

        Returns:
            int: Número de usuários ativos
        """
        pass

    @abstractmethod
    async def find_users_by_role(self, role: str) -> List[User]:
        """
        Busca usuários por role.

        Args:
            role: Role a buscar

        Returns:
            List[User]: Lista de usuários com o role
        """
        pass

    @abstractmethod
    async def ban_user(self, user_id: UserId, reason: str) -> bool:
        """
        Bane um usuário.

        Args:
            user_id: ID do usuário
            reason: Motivo do banimento

        Returns:
            bool: True se baniu com sucesso
        """
        pass

    @abstractmethod
    async def unban_user(self, user_id: UserId) -> bool:
        """
        Remove ban de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se removeu ban com sucesso
        """
        pass

    @abstractmethod
    async def update_last_activity(self, user_id: UserId) -> bool:
        """
        Atualiza última atividade do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se atualizou com sucesso
        """
        pass

    @abstractmethod
    async def get_user_statistics(self, user_id: UserId) -> dict:
        """
        Obtém estatísticas de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            dict: Estatísticas do usuário
        """
        pass