"""
Cliente para integração com HubSoft API.

Responsável por encapsular toda comunicação com a API HubSoft.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class HubSoftClient(ABC):
    """
    Interface abstrata para cliente HubSoft.

    Define o contrato para todas as operações com a API HubSoft.
    """

    @abstractmethod
    async def get_client_data(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados completos do cliente via CPF.

        Args:
            cpf: CPF do cliente (apenas números)

        Returns:
            Dict com dados do cliente ou None se não encontrado
        """
        pass

    @abstractmethod
    async def create_support_ticket(self, ticket_data: Dict[str, Any]) -> Optional[str]:
        """
        Cria ticket de suporte no HubSoft.

        Args:
            ticket_data: Dados do ticket

        Returns:
            ID do ticket criado ou None se erro
        """
        pass

    @abstractmethod
    async def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta status de um ticket no HubSoft.

        Args:
            ticket_id: ID do ticket no HubSoft

        Returns:
            Dados do status ou None se não encontrado
        """
        pass