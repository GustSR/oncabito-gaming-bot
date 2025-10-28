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
    """
    Status do usuário no sistema.

    PENDING_VERIFICATION: Usuário criado mas ainda não verificou CPF
    VERIFIED: CPF verificado, aguardando entrada no grupo
    ACTIVE: Entrou no grupo e está ativo
    INACTIVE: Saiu do grupo ou foi removido
    SUSPENDED: Temporariamente suspenso
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
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
        telegram_user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str],
        cpf: CPF,
        client_name: str,
        service_info: Optional[ServiceInfo] = None,
        is_banned: bool = False,
        ban_reason: Optional[str] = None,
        roles: list = None,
        last_activity_at: Optional[datetime] = None,
        metadata: dict = None,
        expires_at: Optional[datetime] = None,
        rules_accepted: bool = False,
        rules_accepted_at: Optional[datetime] = None
    ):
        super().__init__(user_id)
        self._telegram_user_id = telegram_user_id
        self._username = username
        self._first_name = first_name
        self._last_name = last_name
        self._cpf = cpf
        self._client_name = client_name
        self._service_info = service_info
        self._status = UserStatus.PENDING_VERIFICATION
        self._last_verification = None
        self._is_admin = False
        self._is_banned = is_banned
        self._ban_reason = ban_reason
        self._roles = roles or []
        self._last_activity_at = last_activity_at
        self._metadata = metadata or {}
        self._expires_at = expires_at
        self._rules_accepted = rules_accepted
        self._rules_accepted_at = rules_accepted_at

        # Adiciona evento de registro
        self._add_event(UserRegistered(user_id, cpf, client_name))

    @property
    def telegram_user_id(self) -> int:
        """ID do usuário no Telegram."""
        return self._telegram_user_id

    @property
    def first_name(self) -> str:
        """Primeiro nome do usuário."""
        return self._first_name

    @property
    def last_name(self) -> Optional[str]:
        """Sobrenome do usuário."""
        return self._last_name

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

    @property
    def is_banned(self) -> bool:
        """Se o usuário está banido."""
        return self._is_banned

    @property
    def ban_reason(self) -> Optional[str]:
        """Motivo do banimento."""
        return self._ban_reason

    @property
    def roles(self) -> list:
        """Lista de roles do usuário."""
        return self._roles

    @property
    def last_activity_at(self) -> Optional[datetime]:
        """Data da última atividade."""
        return self._last_activity_at

    @property
    def metadata(self) -> dict:
        """Metadados do usuário."""
        return self._metadata

    @property
    def expires_at(self) -> Optional[datetime]:
        """Data de expiração do registro pendente."""
        return self._expires_at

    @property
    def rules_accepted(self) -> bool:
        """Se o usuário aceitou as regras."""
        return self._rules_accepted

    @property
    def rules_accepted_at(self) -> Optional[datetime]:
        """Data de aceitação das regras."""
        return self._rules_accepted_at

    def mark_rules_accepted(self) -> None:
        """Marca que o usuário aceitou as regras."""
        if self._rules_accepted:
            return  # Já aceitou
        self._rules_accepted = True
        self._rules_accepted_at = datetime.now()
        # self._add_event(RulesAcceptedEvent(self.id)) # Futuro: Adicionar evento de domínio
        self._touch()

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

    def mark_verified(self) -> None:
        """
        Marca o usuário como verificado (CPF validado).

        Transição: PENDING_VERIFICATION → VERIFIED
        """
        if self._status == UserStatus.VERIFIED:
            return  # Já verificado

        self._status = UserStatus.VERIFIED
        self._last_verification = datetime.now()
        self._touch()

    def activate(self) -> None:
        """
        Ativa o usuário no sistema (entrou no grupo).

        Transição: VERIFIED → ACTIVE

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
        self._rules_accepted = False
        self._rules_accepted_at = None
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

        IMPORTANTE: Este método apenas atualiza dados, não muda status do usuário.
        Transições de status devem ser feitas explicitamente pelos event handlers.

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

        # REMOVIDO: Lógica de ativação automática (violava SRP)
        # Transições de status agora são gerenciadas pelos event handlers:
        # - VerificationCompleted → mark_verified() → VERIFIED
        # - NewMemberJoined → activate() → ACTIVE

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

    def is_verified(self) -> bool:
        """
        Verifica se usuário está verificado (CPF OK).

        Returns:
            bool: True se verificado ou ativo
        """
        return self._status in (UserStatus.VERIFIED, UserStatus.ACTIVE)

    def needs_verification(self) -> bool:
        """
        Verifica se usuário precisa de verificação.

        Returns:
            bool: True se precisa verificar
        """
        return self._status == UserStatus.PENDING_VERIFICATION

    def __str__(self) -> str:
        return f"User({self._username}, {self._cpf.masked()}, {self._status.value})"