"""
User Entity - Entidade de usuário do sistema.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

from .base import AggregateRoot, DomainEvent
from ..value_objects.identifiers import UserId
from ..value_objects.cpf import CPF


class UserStatus(Enum):
    """Status do usuário no sistema."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class UserRegistered(DomainEvent):
    """Evento: usuário foi registrado no sistema."""

    def __init__(self, user_id: UserId, cpf: CPF, client_name: str):
        super().__init__()
        self.user_id = user_id
        self.cpf = cpf
        self.client_name = client_name


class UserActivated(DomainEvent):
    """Evento: usuário foi ativado."""

    def __init__(self, user_id: UserId):
        super().__init__()
        self.user_id = user_id


class UserDeactivated(DomainEvent):
    """Evento: usuário foi desativado."""

    def __init__(self, user_id: UserId, reason: str):
        super().__init__()
        self.user_id = user_id
        self.reason = reason


@dataclass
class ServiceInfo:
    """Informações do serviço do cliente."""
    name: str
    status: str
    service_id: Optional[str] = None


class User(AggregateRoot[UserId]):
    """
    Entidade User.

    Representa um usuário do sistema com suas informações
    e regras de negócio associadas.
    """

    def __init__(
        self,
        user_id: UserId,
        username: str,
        cpf: CPF,
        client_name: str,
        service_info: Optional[ServiceInfo] = None
    ):
        super().__init__(user_id)
        self._username = username
        self._cpf = cpf
        self._client_name = client_name
        self._service_info = service_info
        self._status = UserStatus.PENDING_VERIFICATION
        self._last_verification = None
        self._is_admin = False

        # Adiciona evento de registro
        self._add_event(UserRegistered(user_id, cpf, client_name))

    @property
    def username(self) -> str:
        """Username do Telegram."""
        return self._username

    @property
    def cpf(self) -> CPF:
        """CPF do usuário."""
        return self._cpf

    @property
    def client_name(self) -> str:
        """Nome do cliente."""
        return self._client_name

    @property
    def service_info(self) -> Optional[ServiceInfo]:
        """Informações do serviço."""
        return self._service_info

    @property
    def status(self) -> UserStatus:
        """Status atual do usuário."""
        return self._status

    @property
    def last_verification(self) -> Optional[datetime]:
        """Data da última verificação."""
        return self._last_verification

    @property
    def is_admin(self) -> bool:
        """Se o usuário é administrador."""
        return self._is_admin

    def update_username(self, new_username: str) -> None:
        """
        Atualiza o username do usuário.

        Args:
            new_username: Novo username
        """
        self._username = new_username
        self._touch()

    def update_service_info(self, service_info: ServiceInfo) -> None:
        """
        Atualiza informações do serviço.

        Args:
            service_info: Novas informações do serviço
        """
        self._service_info = service_info
        self._touch()

    def activate(self) -> None:
        """
        Ativa o usuário no sistema.

        Raises:
            InvalidStatusTransitionError: Se transição inválida
        """
        if self._status == UserStatus.ACTIVE:
            return  # Já ativo

        self._status = UserStatus.ACTIVE
        self._last_verification = datetime.now()
        self._add_event(UserActivated(self.id))
        self._increment_version()

    def deactivate(self, reason: str) -> None:
        """
        Desativa o usuário no sistema.

        Args:
            reason: Motivo da desativação
        """
        if self._status == UserStatus.INACTIVE:
            return  # Já inativo

        self._status = UserStatus.INACTIVE
        self._add_event(UserDeactivated(self.id, reason))
        self._increment_version()

    def suspend(self, reason: str) -> None:
        """
        Suspende o usuário temporariamente.

        Args:
            reason: Motivo da suspensão
        """
        self._status = UserStatus.SUSPENDED
        self._add_event(UserDeactivated(self.id, f"Suspended: {reason}"))
        self._increment_version()

    def promote_to_admin(self) -> None:
        """Promove usuário a administrador."""
        self._is_admin = True
        self._touch()

    def demote_from_admin(self) -> None:
        """Remove privilégios de administrador."""
        self._is_admin = False
        self._touch()

    def update_client_data(self, client_data: dict) -> None:
        """
        Atualiza dados do cliente com informações do HubSoft.

        Args:
            client_data: Dados retornados pela API HubSoft
        """
        # Atualiza nome se fornecido
        client_name = client_data.get('nome_razaosocial')
        if client_name:
            self._client_name = client_name

        # Atualiza informações de serviço
        servicos = client_data.get('servicos', [])
        if servicos:
            servico = servicos[0]  # Pega o primeiro serviço
            service_name = servico.get('nome', '')
            service_status = servico.get('status', '')
            service_id = servico.get('id')

            self._service_info = ServiceInfo(
                name=service_name,
                status=service_status,
                service_id=service_id
            )

        # Se tem serviço ativo, ativa o usuário automaticamente
        if (self._service_info and
            self._service_info.status.lower() in ['ativo', 'active'] and
            self._status == UserStatus.PENDING_VERIFICATION):
            self.activate()

        self._touch()

    def can_create_ticket(self) -> bool:
        """
        Verifica se usuário pode criar tickets.

        Returns:
            bool: True se pode criar tickets
        """
        return self._status == UserStatus.ACTIVE

    def is_active(self) -> bool:
        """
        Verifica se usuário está ativo.

        Returns:
            bool: True se ativo
        """
        return self._status == UserStatus.ACTIVE

    def needs_verification(self) -> bool:
        """
        Verifica se usuário precisa de verificação.

        Returns:
            bool: True se precisa verificar
        """
        return self._status == UserStatus.PENDING_VERIFICATION

    def __str__(self) -> str:
        return f"User({self._username}, {self._cpf.masked()}, {self._status.value})"