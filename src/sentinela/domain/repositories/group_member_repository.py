"""
Group Member Repository.

Interface abstrata para persistência de membros do grupo.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.group_member import GroupMember, MemberStatus
from ..value_objects.identifiers import UserId


class GroupMemberRepository(ABC):
    """
    Repositório abstrato para membros do grupo.

    Define operações de persistência para GroupMember.
    """

    @abstractmethod
    async def save(self, member: GroupMember) -> GroupMember:
        """
        Salva ou atualiza um membro.

        Args:
            member: Entidade do membro

        Returns:
            GroupMember: Membro salvo
        """
        pass

    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[GroupMember]:
        """
        Busca membro por ID do Telegram.

        Args:
            telegram_id: ID no Telegram

        Returns:
            Optional[GroupMember]: Membro encontrado ou None
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId) -> Optional[GroupMember]:
        """
        Busca membro por UserID.

        Args:
            user_id: ID do usuário

        Returns:
            Optional[GroupMember]: Membro encontrado ou None
        """
        pass

    @abstractmethod
    async def find_all_active(self) -> List[GroupMember]:
        """
        Busca todos os membros ativos.

        Returns:
            List[GroupMember]: Lista de membros ativos
        """
        pass

    @abstractmethod
    async def find_by_status(self, status: MemberStatus) -> List[GroupMember]:
        """
        Busca membros por status.

        Args:
            status: Status desejado

        Returns:
            List[GroupMember]: Lista de membros
        """
        pass

    @abstractmethod
    async def find_inactive_members(self, days: int) -> List[GroupMember]:
        """
        Busca membros inativos há X dias.

        Args:
            days: Número de dias de inatividade

        Returns:
            List[GroupMember]: Lista de membros inativos
        """
        pass

    @abstractmethod
    async def find_unverified_members(self) -> List[GroupMember]:
        """
        Busca membros não verificados.

        Returns:
            List[GroupMember]: Lista de membros não verificados
        """
        pass

    @abstractmethod
    async def find_members_without_contract(self) -> List[GroupMember]:
        """
        Busca membros sem contrato ativo.

        Returns:
            List[GroupMember]: Lista de membros sem contrato
        """
        pass

    @abstractmethod
    async def count_active_members(self) -> int:
        """
        Conta membros ativos.

        Returns:
            int: Número de membros ativos
        """
        pass

    @abstractmethod
    async def delete(self, member_id: UserId) -> bool:
        """
        Remove membro do repositório.

        Args:
            member_id: ID do membro

        Returns:
            bool: True se removeu com sucesso
        """
        pass

    @abstractmethod
    async def exists(self, telegram_id: int) -> bool:
        """
        Verifica se membro existe.

        Args:
            telegram_id: ID no Telegram

        Returns:
            bool: True se existe
        """
        pass