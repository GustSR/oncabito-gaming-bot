"""
Admin Repository Interface.

Define operações para gerenciar administradores do sistema.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime


class AdminRepository(ABC):
    """
    Interface abstrata para repositório de administradores.

    Gerencia a persistência e consulta de administradores
    detectados automaticamente pelo sistema.
    """

    @abstractmethod
    async def is_administrator(self, user_id: int) -> bool:
        """
        Verifica se um usuário é administrador ativo.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            bool: True se é administrador ativo, False caso contrário
        """
        pass

    @abstractmethod
    async def get_administrator(self, user_id: int) -> Optional[dict]:
        """
        Busca dados de um administrador.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            Optional[dict]: Dados do administrador ou None se não encontrado
        """
        pass

    @abstractmethod
    async def list_administrators(self, active_only: bool = True) -> List[dict]:
        """
        Lista todos os administradores.

        Args:
            active_only: Se True, retorna apenas administradores ativos

        Returns:
            List[dict]: Lista de administradores
        """
        pass

    @abstractmethod
    async def save_administrator(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        status: str = "administrator",
        is_active: bool = True
    ) -> bool:
        """
        Salva ou atualiza um administrador.

        Args:
            user_id: ID do usuário no Telegram
            username: Username do Telegram
            first_name: Primeiro nome
            last_name: Sobrenome
            status: Status (administrator, owner, creator)
            is_active: Se está ativo

        Returns:
            bool: True se salvou com sucesso
        """
        pass

    @abstractmethod
    async def deactivate_administrator(self, user_id: int) -> bool:
        """
        Desativa um administrador (não deleta, apenas marca como inativo).

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            bool: True se desativou com sucesso
        """
        pass

    @abstractmethod
    async def sync_from_telegram(self, admin_list: List[dict]) -> int:
        """
        Sincroniza lista de administradores do Telegram.

        Args:
            admin_list: Lista de administradores do Telegram

        Returns:
            int: Número de administradores sincronizados
        """
        pass
