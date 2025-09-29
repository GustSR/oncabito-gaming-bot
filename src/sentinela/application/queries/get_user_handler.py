"""
Get User Query Handler.

Handler para buscar usuários.
"""

import logging
from typing import Optional

from .get_user_query import GetUserQuery
from ...domain.repositories.user_repository import UserRepository
from ...domain.entities.user import User

logger = logging.getLogger(__name__)


class GetUserHandler:
    """
    Handler para query GetUser.

    Responsável por:
    - Buscar usuário no repository
    - Retornar resultado ou None
    """

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    async def handle(self, query: GetUserQuery) -> Optional[User]:
        """
        Processa query de busca de usuário.

        Args:
            query: Query com ID do usuário

        Returns:
            User: Usuário encontrado ou None

        Raises:
            ValidationError: Se ID inválido
            RepositoryError: Se erro na consulta
        """
        logger.debug(f"Getting user: {query.user_id}")

        try:
            # Converte para objeto de domínio
            user_id = query.to_domain_id()

            # Busca no repository
            user = await self._user_repository.find_by_id(user_id)

            if user:
                logger.debug(f"User found: {user.username}")
            else:
                logger.debug(f"User {query.user_id} not found")

            return user

        except Exception as e:
            logger.error(f"Error getting user {query.user_id}: {e}")
            raise