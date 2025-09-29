"""
Implementação do cliente HubSoft usando a integração existente.
"""

import logging
from typing import Optional, Dict, Any

from .hubsoft_client import HubSoftClient

logger = logging.getLogger(__name__)


class HubSoftClientImpl(HubSoftClient):
    """
    Implementação concreta do cliente HubSoft.

    Utiliza a integração existente como base, mas com interface limpa.
    """

    async def get_client_data(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados completos do cliente via CPF.

        Args:
            cpf: CPF do cliente (apenas números)

        Returns:
            Dict com dados do cliente ou None se não encontrado
        """
        try:
            # Importa aqui para evitar circular imports durante inicialização
            from ...integrations.hubsoft import cliente as hubsoft_cliente

            logger.info(f"Buscando dados do cliente via HubSoft para CPF {cpf[:3]}***")
            client_data = hubsoft_cliente.get_client_data(cpf)

            if client_data:
                logger.info(f"Dados do cliente encontrados para CPF {cpf[:3]}***")
                return client_data
            else:
                logger.warning(f"Nenhum dado encontrado para CPF {cpf[:3]}***")
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar dados do cliente: {e}")
            return None

    async def create_support_ticket(self, ticket_data: Dict[str, Any]) -> Optional[str]:
        """
        Cria ticket de suporte no HubSoft.

        Args:
            ticket_data: Dados do ticket

        Returns:
            ID do ticket criado ou None se erro
        """
        try:
            # Implementação futura - por enquanto retorna None
            logger.info("Criação de tickets via HubSoft não implementada ainda")
            return None

        except Exception as e:
            logger.error(f"Erro ao criar ticket no HubSoft: {e}")
            return None

    async def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta status de um ticket no HubSoft.

        Args:
            ticket_id: ID do ticket no HubSoft

        Returns:
            Dados do status ou None se não encontrado
        """
        try:
            # Implementação futura - por enquanto retorna None
            logger.info(f"Consulta de status do ticket {ticket_id} não implementada ainda")
            return None

        except Exception as e:
            logger.error(f"Erro ao consultar status do ticket {ticket_id}: {e}")
            return None