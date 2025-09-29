"""
Base interface para todos os repositories.

Define o contrato básico que todos os repositories devem seguir.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List
from ..entities.base import Entity

EntityType = TypeVar('EntityType', bound=Entity)
EntityIdType = TypeVar('EntityIdType')


class Repository(Generic[EntityType, EntityIdType], ABC):
    """
    Interface base para repositories.

    Define operações CRUD básicas que todos os repositories
    devem implementar.
    """

    @abstractmethod
    async def save(self, entity: EntityType) -> None:
        """
        Salva uma entidade.

        Args:
            entity: Entidade a ser salva

        Raises:
            RepositoryError: Em caso de erro na persistência
        """
        pass

    @abstractmethod
    async def find_by_id(self, entity_id: EntityIdType) -> Optional[EntityType]:
        """
        Busca entidade por ID.

        Args:
            entity_id: ID da entidade

        Returns:
            EntityType: Entidade encontrada ou None

        Raises:
            RepositoryError: Em caso de erro na consulta
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: EntityIdType) -> bool:
        """
        Remove entidade por ID.

        Args:
            entity_id: ID da entidade

        Returns:
            bool: True se removida, False se não encontrada

        Raises:
            RepositoryError: Em caso de erro na remoção
        """
        pass

    @abstractmethod
    async def exists(self, entity_id: EntityIdType) -> bool:
        """
        Verifica se entidade existe.

        Args:
            entity_id: ID da entidade

        Returns:
            bool: True se existe, False caso contrário

        Raises:
            RepositoryError: Em caso de erro na consulta
        """
        pass


class RepositoryError(Exception):
    """Erro base para operações de repository."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class EntityNotFoundError(RepositoryError):
    """Entidade não encontrada."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} with ID {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateEntityError(RepositoryError):
    """Tentativa de criar entidade duplicada."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} with ID {entity_id} already exists")
        self.entity_type = entity_type
        self.entity_id = entity_id