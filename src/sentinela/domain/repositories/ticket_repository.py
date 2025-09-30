"""
Ticket Repository Interface.

Define o contrato para persistência de tickets de suporte.
"""

from abc import abstractmethod
from typing import List, Optional
from datetime import datetime

from .base import Repository
from ..entities.ticket import Ticket, TicketStatus
from ..value_objects.identifiers import TicketId, UserId, HubSoftId


class TicketRepository(Repository[Ticket, TicketId]):
    """
    Interface para persistência de tickets.

    Define operações específicas para a entidade Ticket.
    """

    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> List[Ticket]:
        """
        Busca tickets por usuário.

        Args:
            user_id: ID do usuário

        Returns:
            List[Ticket]: Lista de tickets do usuário
        """
        pass

    @abstractmethod
    async def find_by_status(self, status: TicketStatus) -> List[Ticket]:
        """
        Busca tickets por status.

        Args:
            status: Status dos tickets

        Returns:
            List[Ticket]: Lista de tickets com o status
        """
        pass

    @abstractmethod
    async def find_active_tickets(self) -> List[Ticket]:
        """
        Busca todos os tickets ativos (não finalizados).

        Returns:
            List[Ticket]: Lista de tickets ativos
        """
        pass

    @abstractmethod
    async def find_by_hubsoft_id(self, hubsoft_id: HubSoftId) -> Optional[Ticket]:
        """
        Busca ticket por ID do HubSoft.

        Args:
            hubsoft_id: ID no HubSoft

        Returns:
            Optional[Ticket]: Ticket encontrado ou None
        """
        pass

    @abstractmethod
    async def find_active_by_user(self, user_id: UserId) -> List[Ticket]:
        """
        Busca tickets ativos de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            List[Ticket]: Lista de tickets ativos do usuário
        """
        pass

    @abstractmethod
    async def find_pending_sync(self) -> List[Ticket]:
        """
        Busca tickets pendentes de sincronização com HubSoft.

        Returns:
            List[Ticket]: Lista de tickets para sincronizar
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Ticket]:
        """
        Busca tickets criados em um período.

        Args:
            start_date: Data inicial
            end_date: Data final

        Returns:
            List[Ticket]: Lista de tickets no período
        """
        pass

    @abstractmethod
    async def count_active_by_user(self, user_id: UserId) -> int:
        """
        Conta tickets ativos de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            int: Número de tickets ativos
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: TicketStatus) -> int:
        """
        Conta tickets por status.

        Args:
            status: Status a contar

        Returns:
            int: Número de tickets com o status
        """
        pass

    @abstractmethod
    async def get_user_ticket_statistics(self, user_id: UserId) -> dict:
        """
        Obtém estatísticas de tickets de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            dict: Estatísticas do usuário
        """
        pass

    @abstractmethod
    async def find_tickets_with_attachments(self) -> List[Ticket]:
        """
        Busca tickets que possuem anexos.

        Returns:
            List[Ticket]: Lista de tickets com anexos
        """
        pass

    @abstractmethod
    async def update_sync_status(
        self,
        ticket_id: TicketId,
        sync_status: str,
        hubsoft_id: Optional[HubSoftId] = None,
        sync_error: Optional[str] = None
    ) -> bool:
        """
        Atualiza status de sincronização de um ticket.

        Args:
            ticket_id: ID do ticket
            sync_status: Novo status de sincronização
            hubsoft_id: ID no HubSoft (se sincronizado)
            sync_error: Erro de sincronização (se houver)

        Returns:
            bool: True se atualizou com sucesso
        """
        pass