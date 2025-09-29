"""
Implementação do cliente de convites usando serviços existentes.
"""

import logging
from typing import Optional

from .invite_client import InviteClient

logger = logging.getLogger(__name__)


class InviteClientImpl(InviteClient):
    """
    Implementação concreta do cliente de convites.

    Utiliza os serviços existentes como base.
    """

    async def create_temporary_invite_link(self, user_id: int, username: str) -> Optional[str]:
        """
        Cria link temporário de convite para o grupo.

        Args:
            user_id: ID do usuário no Telegram
            username: Username do usuário

        Returns:
            Link de convite ou None se erro
        """
        try:
            # Importa aqui para evitar circular imports durante inicialização
            from ...services.invite_service import create_temporary_invite_link

            logger.info(f"Criando link temporário para usuário {username} (ID: {user_id})")
            invite_link = await create_temporary_invite_link(user_id, username)

            if invite_link:
                logger.info(f"Link criado com sucesso para usuário {username} (ID: {user_id})")
                return invite_link
            else:
                logger.warning(f"Falha ao criar link para usuário {username} (ID: {user_id})")
                return None

        except Exception as e:
            logger.error(f"Erro ao criar link de convite para usuário {user_id}: {e}")
            return None