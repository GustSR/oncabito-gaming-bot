"""
Implementação do cliente de grupos usando serviços existentes.
"""

import logging
from typing import TYPE_CHECKING

from .group_client import GroupClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GroupClientImpl(GroupClient):
    """
    Implementação concreta do cliente de grupos.

    Utiliza os serviços existentes como base.
    """

    async def is_user_in_group(self, user_id: int) -> bool:
        """
        Verifica se usuário está no grupo.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            True se usuário está no grupo, False caso contrário
        """
        try:
            # Importa aqui para evitar circular imports durante inicialização
            from ...services.group_service import is_user_in_group

            logger.info(f"Verificando se usuário {user_id} está no grupo...")
            result = await is_user_in_group(user_id)

            logger.info(f"Usuário {user_id} {'está' if result else 'não está'} no grupo")
            return result

        except Exception as e:
            logger.error(f"Erro ao verificar se usuário {user_id} está no grupo: {e}")
            return False

    async def remove_user_from_group(self, user_id: int) -> bool:
        """
        Remove usuário do grupo.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            True se removeu com sucesso, False caso contrário
        """
        try:
            # Implementação futura - usar serviços existentes ou implementar
            logger.info(f"Remoção de usuário {user_id} do grupo não implementada ainda")
            return False

        except Exception as e:
            logger.error(f"Erro ao remover usuário {user_id} do grupo: {e}")
            return False