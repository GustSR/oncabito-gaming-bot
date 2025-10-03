"""
Repository interface para CPF Verification.

Define as operações de persistência para verificações de CPF.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .base import Repository
from ..entities.cpf_verification import CPFVerificationRequest, VerificationId, VerificationStatus, VerificationType
from ..value_objects.identifiers import UserId


class CPFVerificationRepository(Repository[CPFVerificationRequest, VerificationId], ABC):
    """
    Repository para operações com verificações de CPF.

    Extends o repository base com operações específicas
    para o domínio de verificação de CPF.
    """

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId, limit: int = 10) -> List[CPFVerificationRequest]:
        """
        Busca verificações para um usuário.

        Args:
            user_id: ID do usuário
            limit: Número máximo de verificações a retornar

        Returns:
            List[CPFVerificationRequest]: Lista de verificações do usuário
        """
        pass

    @abstractmethod
    async def find_pending_by_user(self, user_id: UserId) -> Optional[CPFVerificationRequest]:
        """
        Busca verificação pendente específica para um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Optional[CPFVerificationRequest]: Verificação pendente ou None
        """
        pass

    @abstractmethod
    async def find_by_status(self, status: VerificationStatus) -> List[CPFVerificationRequest]:
        """
        Busca verificações por status.

        Args:
            status: Status da verificação

        Returns:
            List[CPFVerificationRequest]: Lista de verificações
        """
        pass

    @abstractmethod
    async def find_expired_verifications(self) -> List[CPFVerificationRequest]:
        """
        Busca verificações expiradas.

        Returns:
            List[CPFVerificationRequest]: Verificações expiradas
        """
        pass

    @abstractmethod
    async def find_by_verification_type(self, verification_type: VerificationType) -> List[CPFVerificationRequest]:
        """
        Busca verificações por tipo.

        Args:
            verification_type: Tipo de verificação

        Returns:
            List[CPFVerificationRequest]: Lista de verificações
        """
        pass

    @abstractmethod
    async def find_recent_verifications(self, hours: int = 24) -> List[CPFVerificationRequest]:
        """
        Busca verificações recentes.

        Args:
            hours: Número de horas para considerar como recente

        Returns:
            List[CPFVerificationRequest]: Verificações recentes
        """
        pass

    @abstractmethod
    async def count_attempts_by_user(self, user_id: UserId, hours: int = 24) -> int:
        """
        Conta tentativas de verificação de um usuário em um período.

        Args:
            user_id: ID do usuário
            hours: Período em horas

        Returns:
            int: Número de tentativas
        """
        pass

    @abstractmethod
    async def find_by_cpf(self, cpf: str) -> List[CPFVerificationRequest]:
        """
        Busca verificações por CPF fornecido.

        Args:
            cpf: CPF a ser buscado

        Returns:
            List[CPFVerificationRequest]: Verificações relacionadas ao CPF
        """
        pass

    @abstractmethod
    async def cleanup_old_verifications(self, days_old: int = 30) -> int:
        """
        Remove verificações antigas do sistema.

        Args:
            days_old: Idade em dias para considerar como antiga

        Returns:
            int: Número de verificações removidas
        """
        pass

    @abstractmethod
    async def get_verification_stats(self) -> dict:
        """
        Retorna estatísticas de verificações.

        Returns:
            dict: Estatísticas agrupadas por status, tipo, etc.
        """
        pass

    @abstractmethod
    async def find_conflicting_verifications(self, cpf: str, user_id: UserId) -> List[CPFVerificationRequest]:
        """
        Busca verificações que podem gerar conflito de CPF.

        Args:
            cpf: CPF a verificar
            user_id: ID do usuário atual

        Returns:
            List[CPFVerificationRequest]: Verificações conflitantes
        """
        pass