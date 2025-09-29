"""
Create User Command Handler.

Handler para processar comandos de criação de usuário.
"""

import logging
from typing import Optional

from .create_user_command import CreateUserCommand
from ...domain.repositories.user_repository import UserRepository
from ...domain.entities.user import User, ServiceInfo
from ...domain.repositories.base import DuplicateEntityError

logger = logging.getLogger(__name__)


class CreateUserHandler:
    """
    Handler para comando CreateUser.

    Responsável por:
    - Validar se usuário não existe
    - Criar entidade User
    - Persistir no repository
    - Retornar resultado
    """

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    async def handle(self, command: CreateUserCommand) -> User:
        """
        Processa comando de criação de usuário.

        Args:
            command: Comando com dados do usuário

        Returns:
            User: Usuário criado

        Raises:
            UserAlreadyExistsError: Se usuário já existe
            ValidationError: Se dados inválidos
            RepositoryError: Se erro na persistência
        """
        logger.info(f"Creating user: {command.username} (ID: {command.user_id})")

        try:
            # Converte para objetos de domínio
            user_id, cpf = command.to_domain_objects()

            # Verifica se usuário já existe
            existing_user = await self._user_repository.find_by_id(user_id)
            if existing_user:
                raise UserAlreadyExistsError(f"User with ID {user_id} already exists")

            # Verifica se CPF já está em uso
            existing_cpf = await self._user_repository.find_by_cpf(cpf)
            if existing_cpf:
                raise CPFAlreadyInUseError(f"CPF {cpf.masked()} already in use")

            # Cria service info se fornecido
            service_info = None
            if command.service_name:
                service_info = ServiceInfo(
                    name=command.service_name,
                    status=command.service_status or 'unknown'
                )

            # Cria entidade User
            user = User(
                user_id=user_id,
                username=command.username,
                cpf=cpf,
                client_name=command.client_name,
                service_info=service_info
            )

            # Persiste no repository
            await self._user_repository.save(user)

            logger.info(f"User created successfully: {user.id}")
            return user

        except Exception as e:
            logger.error(f"Error creating user {command.username}: {e}")
            raise


class UserAlreadyExistsError(Exception):
    """Usuário já existe no sistema."""
    pass


class CPFAlreadyInUseError(Exception):
    """CPF já está sendo usado por outro usuário."""
    pass