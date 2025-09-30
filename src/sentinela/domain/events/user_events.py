"""
Domain Events relacionados a usuários.

Define os eventos que são disparados quando
o estado dos usuários muda.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..entities.base import DomainEvent
from ..value_objects.identifiers import UserId


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """
    Evento disparado quando um novo usuário se registra.

    Attributes:
        user_id: ID do usuário registrado
        username: Nome de usuário
        registration_date: Data/hora do registro
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    registration_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class UserBanned(DomainEvent):
    """
    Evento disparado quando um usuário é banido.

    Attributes:
        user_id: ID do usuário banido
        username: Nome de usuário
        reason: Motivo do banimento
        banned_by: Quem aplicou o banimento
        ban_date: Data/hora do banimento
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    reason: str
    banned_by: str
    ban_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class UserUnbanned(DomainEvent):
    """
    Evento disparado quando um usuário é desbanido.

    Attributes:
        user_id: ID do usuário desbanido
        username: Nome de usuário
        unbanned_by: Quem removeu o banimento
        unban_date: Data/hora da remoção do banimento
        occurred_at: Timestamp do evento
    """
    user_id: int
    username: str
    unbanned_by: str
    unban_date: datetime
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class CPFValidated(DomainEvent):
    """
    Evento disparado quando um CPF é validado.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        cpf_number: Número do CPF
        is_valid: Se o CPF é válido
        validation_date: Data/hora da validação
    """
    user_id: int
    username: str
    cpf_number: str
    is_valid: bool
    validation_date: Optional[datetime] = None

    def __post_init__(self):
        if self.validation_date is None:
            object.__setattr__(self, 'validation_date', datetime.now())


@dataclass(frozen=True)
class UserProfileUpdated(DomainEvent):
    """
    Evento disparado quando o perfil de um usuário é atualizado.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        updated_fields: Campos que foram atualizados
        updated_by: Quem fez a atualização
    """
    user_id: int
    username: str
    updated_fields: dict
    updated_by: str


@dataclass(frozen=True)
class UserLastSeenUpdated(DomainEvent):
    """
    Evento disparado quando a última atividade do usuário é atualizada.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        last_seen: Última atividade registrada
        activity_type: Tipo de atividade (message, command, etc.)
    """
    user_id: int
    username: str
    last_seen: datetime
    activity_type: str


@dataclass(frozen=True)
class UserPermissionGrantedEvent(DomainEvent):
    """
    Evento disparado quando permissões são concedidas a um usuário.

    Attributes:
        user_id: ID do usuário
        permission_level: Nível de permissão concedido
        granted_by: ID do admin que concedeu (None se automático)
        granted_at: Data/hora da concessão
    """
    user_id: UserId
    permission_level: 'PermissionLevel'  # Forward reference
    granted_by: Optional[int]
    granted_at: datetime


@dataclass(frozen=True)
class UserAccessRevokedEvent(DomainEvent):
    """
    Evento disparado quando acesso de um usuário é revogado.

    Attributes:
        user_id: ID do usuário
        reason: Motivo da revogação
        revoked_by: ID do admin que revogou
        revoked_at: Data/hora da revogação
    """
    user_id: UserId
    reason: str
    revoked_by: int
    revoked_at: datetime


@dataclass(frozen=True)
class UserPromotedEvent(DomainEvent):
    """
    Evento disparado quando usuário é promovido a novo nível.

    Attributes:
        user_id: ID do usuário
        new_level: Novo nível de permissão
        promoted_by: ID do admin que promoveu
        promoted_at: Data/hora da promoção
    """
    user_id: UserId
    new_level: 'PermissionLevel'  # Forward reference
    promoted_by: int
    promoted_at: datetime


@dataclass(frozen=True)
class AdminNotificationRequiredEvent(DomainEvent):
    """
    Evento disparado quando admins precisam ser notificados.

    Attributes:
        user_id: ID do usuário relacionado
        notification_type: Tipo de notificação
        message: Mensagem a ser enviada
        channel_id: ID do canal de notificação
        created_at: Data/hora da criação
    """
    user_id: UserId
    notification_type: str
    message: str
    channel_id: int
    created_at: datetime


@dataclass(frozen=True)
class InviteLinkRequestedEvent(DomainEvent):
    """
    Evento disparado quando um link de convite é solicitado.

    Attributes:
        user_id: ID do usuário para quem o link é criado
        invite_data: Dados do convite (configurações)
        created_at: Data/hora da solicitação
    """
    user_id: UserId
    invite_data: dict
    created_at: datetime


@dataclass(frozen=True)
class InviteLinkCreatedEvent(DomainEvent):
    """
    Evento disparado quando um link de convite é criado no Telegram.

    Attributes:
        user_id: ID do usuário para quem foi criado
        invite_url: URL do link criado
        expire_date: Data de expiração
        member_limit: Limite de membros
        created_by: ID de quem criou
        created_at: Data/hora da criação
    """
    user_id: UserId
    invite_url: str
    expire_date: datetime
    member_limit: int
    created_by: int
    created_at: datetime


@dataclass(frozen=True)
class InviteLinkRevokedEvent(DomainEvent):
    """
    Evento disparado quando um link de convite é revogado.

    Attributes:
        invite_url: URL do link revogado
        reason: Motivo da revogação
        revoked_by: ID de quem revogou (None se automático)
        revoked_at: Data/hora da revogação
    """
    invite_url: str
    reason: str
    revoked_by: Optional[int]
    revoked_at: datetime


@dataclass(frozen=True)
class InviteLinkUsedEvent(DomainEvent):
    """
    Evento disparado quando um link de convite é usado.

    Attributes:
        invite_url: URL do link usado
        user_id: ID do usuário que usou
        username: Nome do usuário
        used_at: Data/hora do uso
    """
    invite_url: str
    user_id: int
    username: str
    used_at: datetime


@dataclass(frozen=True)
class InviteLinkExpiredEvent(DomainEvent):
    """
    Evento disparado quando um link de convite expira.

    Attributes:
        invite_url: URL do link expirado
        created_for: ID do usuário para quem foi criado
        expired_at: Data/hora da expiração
    """
    invite_url: str
    created_for: int
    expired_at: datetime


@dataclass(frozen=True)
class InviteCleanupRequestedEvent(DomainEvent):
    """
    Evento disparado quando limpeza de convites é solicitada.

    Attributes:
        requested_at: Data/hora da solicitação
    """
    requested_at: datetime


@dataclass(frozen=True)
class NewMemberJoinedEvent(DomainEvent):
    """
    Evento disparado quando novo membro entra no grupo.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        first_name: Primeiro nome
        joined_at: Data/hora de entrada
    """
    user_id: int
    username: str
    first_name: str
    joined_at: datetime


@dataclass(frozen=True)
class RulesAcceptedEvent(DomainEvent):
    """
    Evento disparado quando usuário aceita as regras.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        access_granted: Se acesso gaming foi concedido
        accepted_at: Data/hora da aceitação
    """
    user_id: int
    username: str
    access_granted: bool
    accepted_at: datetime


@dataclass(frozen=True)
class GamingAccessRequestedEvent(DomainEvent):
    """
    Evento disparado quando acesso gaming é solicitado.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        requested_at: Data/hora da solicitação
    """
    user_id: int
    username: str
    requested_at: datetime


@dataclass(frozen=True)
class WelcomeMessageSentEvent(DomainEvent):
    """
    Evento disparado quando mensagem de boas-vindas é enviada.

    Attributes:
        user_id: ID do usuário
        message_type: Tipo de mensagem enviada
        sent_at: Data/hora do envio
    """
    user_id: int
    message_type: str
    sent_at: datetime