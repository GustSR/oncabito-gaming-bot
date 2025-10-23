"""
Repository interface para Duplicate Conflicts.

Define as operações de persistência para conflitos de CPF duplicado.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .base import Repository
from ..entities.duplicate_conflict import DuplicateConflict, ConflictId, ConflictStatus


class DuplicateConflictRepository(Repository[DuplicateConflict, ConflictId], ABC):
    """
    Repository para operações com conflitos de CPF duplicado.

    Extends o repository base com operações específicas
    para o domínio de conflitos de duplicata.
    """

    @abstractmethod
    async def find_by_cpf_hash(self, cpf_hash: str) -> List[DuplicateConflict]:
        """
        Busca conflitos por hash de CPF.

        Args:
            cpf_hash: Hash do CPF

        Returns:
            List[DuplicateConflict]: Lista de conflitos associados ao CPF
        """
        pass

    @abstractmethod
    async def find_by_status(self, status: ConflictStatus) -> List[DuplicateConflict]:
        """
        Busca conflitos por status.

        Args:
            status: Status do conflito

        Returns:
            List[DuplicateConflict]: Lista de conflitos
        """
        pass

    @abstractmethod
    async def find_pending_conflicts(self) -> List[DuplicateConflict]:
        """
        Busca todos os conflitos pendentes.

        Returns:
            List[DuplicateConflict]: Conflitos com status PENDING
        """
        pass

    @abstractmethod
    async def find_expired_pending_conflicts(self) -> List[DuplicateConflict]:
        """
        Busca conflitos pendentes que já expiraram.

        Returns:
            List[DuplicateConflict]: Conflitos PENDING com expires_at < now()
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: int) -> List[DuplicateConflict]:
        """
        Busca conflitos envolvendo um usuário específico.

        Args:
            user_id: ID do usuário

        Returns:
            List[DuplicateConflict]: Conflitos que incluem o usuário
        """
        pass

    @abstractmethod
    async def find_by_notified_user(self, user_id: int) -> List[DuplicateConflict]:
        """
        Busca conflitos onde um usuário foi notificado.

        Args:
            user_id: ID do usuário notificado

        Returns:
            List[DuplicateConflict]: Conflitos onde este usuário foi notificado
        """
        pass

    @abstractmethod
    async def exists_pending_for_cpf(self, cpf_hash: str) -> bool:
        """
        Verifica se já existe um conflito pendente para um CPF.

        Args:
            cpf_hash: Hash do CPF

        Returns:
            bool: True se já existe conflito pendente
        """
        pass

    @abstractmethod
    async def get_conflict_statistics(self, days: int = 30) -> dict:
        """
        Obtém estatísticas de conflitos.

        Args:
            days: Período em dias para análise

        Returns:
            dict: Estatísticas de conflitos (total, por status, etc)
        """
        pass

    @abstractmethod
    async def cleanup_old_resolved_conflicts(self, days_old: int = 90) -> int:
        """
        Remove conflitos resolvidos antigos do sistema.

        Args:
            days_old: Idade em dias para considerar como antigo

        Returns:
            int: Número de conflitos removidos
        """
        pass
