"""
User Repository Interface.

Define o contrato para persistência de usuários.
"""

from abc import abstractmethod
from typing import List, Optional

from .base import Repository
from ..entities.user import User
from ..value_objects.identifiers import UserId
from ..value_objects.cpf import CPF


class UserRepository(Repository[User, UserId]):
    """
    Interface para persistência de usuários.

    Define operações específicas para a entidade User.
    """

    @abstractmethod
    async def find_by_cpf(self, cpf: CPF) -> Optional[User]:
        """
        Busca usuário por CPF.

        Args:
            cpf: CPF do usuário

        Returns:
            User: Usuário encontrado ou None
        """
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        """
        Busca usuário por username.

        Args:
            username: Username do Telegram

        Returns:
            User: Usuário encontrado ou None
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
    async def find_pending_verification(self) -> List[User]:
        """
        Busca usuários pendentes de verificação.

        Returns:
            List[User]: Lista de usuários pendentes
        """
        pass

    @abstractmethod
    async def find_admins(self) -> List[User]:
        """
        Busca usuários administradores.

        Returns:
            List[User]: Lista de administradores
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
    async def exists_by_cpf(self, cpf: CPF) -> bool:
        """
        Verifica se existe usuário com o CPF.

        Args:
            cpf: CPF a verificar

        Returns:
            bool: True se existe
        """
        pass

    @abstractmethod
    async def mark_user_inactive(self, user_id: UserId) -> bool:
        """
        Marca usuário como inativo.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se marcou com sucesso
        """
        pass

    @abstractmethod
    async def update_user_id_for_cpf(self, cpf: CPF, new_user_id: UserId, new_username: str) -> bool:
        """
        Atualiza o user_id para um registro baseado no CPF.

        Args:
            cpf: CPF do registro a atualizar
            new_user_id: Novo ID do usuário
            new_username: Novo username

        Returns:
            bool: True se atualizou com sucesso
        """
        pass