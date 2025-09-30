"""
Permission Management Use Case.

Coordena operações relacionadas a permissões de usuários,
incluindo concessão, revogação e verificação de acessos.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.repositories.user_repository import UserRepository
from ...domain.services.permission_service import (
    PermissionDomainService,
    TopicConfiguration
)
from ...domain.value_objects.permission_level import (
    PermissionLevel,
    UserPermissions
)
from ...domain.value_objects.identifiers import UserId
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class PermissionGrantResult:
    """Resultado de concessão de permissão."""

    success: bool
    message: str
    permissions: Optional[UserPermissions] = None
    requires_manual_action: bool = False
    admin_notification_sent: bool = False


class PermissionManagementUseCase(UseCase):
    """
    Use Case para gerenciamento de permissões.

    Coordena operações de concessão, revogação e validação
    de permissões de usuários no sistema.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        permission_service: PermissionDomainService,
        event_bus: EventBus
    ):
        """
        Inicializa o use case.

        Args:
            user_repository: Repositório de usuários
            permission_service: Serviço de domínio de permissões
            event_bus: Event bus para publicar eventos
        """
        self.user_repository = user_repository
        self.permission_service = permission_service
        self.event_bus = event_bus

    async def grant_gaming_access(
        self,
        user_id: int,
        username: str,
        granted_by: Optional[int] = None
    ) -> PermissionGrantResult:
        """
        Concede acesso aos tópicos de gaming para usuário verificado.

        Args:
            user_id: ID do usuário no Telegram
            username: Nome do usuário
            granted_by: ID do admin que concedeu (None se automático)

        Returns:
            PermissionGrantResult: Resultado da operação
        """
        try:
            logger.info(f"Concedendo acesso gaming para {username} (ID: {user_id})")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                logger.warning(f"Usuário {user_id} não encontrado")
                return PermissionGrantResult(
                    success=False,
                    message="Usuário não encontrado no sistema"
                )

            # Verifica se pode conceder acesso
            if not self.permission_service.can_grant_gaming_access(user):
                logger.warning(f"Não é possível conceder acesso para {username}")
                return PermissionGrantResult(
                    success=False,
                    message="Usuário não atende aos requisitos para acesso gaming"
                )

            # Cria novas permissões
            new_permissions = self.permission_service.create_permissions_after_verification(user)

            if not new_permissions:
                logger.error(f"Falha ao criar permissões para {username}")
                return PermissionGrantResult(
                    success=False,
                    message="Erro ao gerar permissões"
                )

            # Atualiza usuário com novas permissões
            # (Aqui você poderia salvar as permissões no banco se necessário)

            # Publica evento de permissão concedida
            from ...domain.events.user_events import UserPermissionGrantedEvent

            await self.event_bus.publish(
                UserPermissionGrantedEvent(
                    aggregate_id=user.id.value,
                    user_id=user.id,
                    permission_level=new_permissions.level,
                    granted_by=granted_by,
                    granted_at=datetime.now()
                )
            )

            logger.info(f"Acesso gaming concedido com sucesso para {username}")

            # Verifica se precisa notificar admins
            requires_manual = self.permission_service.should_notify_admins(user)

            return PermissionGrantResult(
                success=True,
                message=self.permission_service.get_permission_grant_message(
                    user,
                    new_permissions
                ),
                permissions=new_permissions,
                requires_manual_action=requires_manual
            )

        except Exception as e:
            logger.error(f"Erro ao conceder acesso gaming: {e}")
            return PermissionGrantResult(
                success=False,
                message="Erro interno ao conceder acesso"
            )

    async def revoke_access(
        self,
        user_id: int,
        reason: str,
        revoked_by: int
    ) -> UseCaseResult:
        """
        Revoga acesso de um usuário.

        Args:
            user_id: ID do usuário no Telegram
            reason: Motivo da revogação
            revoked_by: ID do admin que revogou

        Returns:
            UseCaseResult: Resultado da operação
        """
        try:
            logger.info(f"Revogando acesso do usuário {user_id}. Motivo: {reason}")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                return UseCaseResult(
                    success=False,
                    message="Usuário não encontrado"
                )

            # Bane o usuário no repositório
            success = await self.user_repository.ban_user(
                user.id,
                reason
            )

            if not success:
                return UseCaseResult(
                    success=False,
                    message="Erro ao revogar acesso"
                )

            # Publica evento
            from ...domain.events.user_events import UserAccessRevokedEvent

            await self.event_bus.publish(
                UserAccessRevokedEvent(
                    aggregate_id=user.id.value,
                    user_id=user.id,
                    reason=reason,
                    revoked_by=revoked_by,
                    revoked_at=datetime.now()
                )
            )

            logger.info(f"Acesso revogado com sucesso para usuário {user_id}")

            return UseCaseResult(
                success=True,
                message=f"Acesso revogado com sucesso. Motivo: {reason}"
            )

        except Exception as e:
            logger.error(f"Erro ao revogar acesso: {e}")
            return UseCaseResult(
                success=False,
                message="Erro interno ao revogar acesso"
            )

    async def check_user_permissions(
        self,
        user_id: int
    ) -> UseCaseResult:
        """
        Verifica permissões atuais de um usuário.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            UseCaseResult: Resultado com permissões atuais
        """
        try:
            logger.info(f"Verificando permissões do usuário {user_id}")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                return UseCaseResult(
                    success=False,
                    message="Usuário não encontrado"
                )

            # Determina nível de permissão baseado no status do usuário
            if user.is_banned:
                permissions = UserPermissions.create_restricted()
            elif user.is_verified:
                # Calcula tópicos de gaming
                gaming_topics = self.permission_service.calculate_gaming_topics()
                permissions = UserPermissions.create_gamer(gaming_topics)
            else:
                permissions = UserPermissions.create_restricted()

            permission_data = {
                "level": permissions.level.value,
                "can_send_messages": permissions.can_send_messages,
                "can_send_media": permissions.can_send_media,
                "has_gaming_access": permissions.has_gaming_access(),
                "is_banned": permissions.is_banned,
                "topic_count": len(permissions.topic_access)
            }

            return UseCaseResult(
                success=True,
                message="Permissões obtidas com sucesso",
                data=permission_data
            )

        except Exception as e:
            logger.error(f"Erro ao verificar permissões: {e}")
            return UseCaseResult(
                success=False,
                message="Erro ao verificar permissões"
            )

    async def notify_admins_about_verification(
        self,
        user_id: int,
        notification_channel_id: int
    ) -> bool:
        """
        Notifica administradores sobre usuário verificado.

        Args:
            user_id: ID do usuário verificado
            notification_channel_id: ID do canal de notificações

        Returns:
            bool: True se notificação foi enviada
        """
        try:
            logger.info(f"Notificando admins sobre usuário {user_id}")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                logger.warning(f"Usuário {user_id} não encontrado")
                return False

            # Calcula permissões que seriam concedidas
            permissions = self.permission_service.create_permissions_after_verification(user)

            if not permissions:
                return False

            # Gera mensagem de notificação
            message = self.permission_service.get_admin_notification_message(
                user,
                permissions
            )

            # Publica evento de notificação
            from ...domain.events.user_events import AdminNotificationRequiredEvent

            await self.event_bus.publish(
                AdminNotificationRequiredEvent(
                    aggregate_id=user.id.value,
                    user_id=user.id,
                    notification_type="user_verification",
                    message=message,
                    channel_id=notification_channel_id,
                    created_at=datetime.now()
                )
            )

            logger.info(f"Notificação de admin enviada para usuário {user_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao notificar admins: {e}")
            return False

    async def promote_user(
        self,
        user_id: int,
        new_level: PermissionLevel,
        promoted_by: int
    ) -> UseCaseResult:
        """
        Promove usuário para novo nível de permissão.

        Args:
            user_id: ID do usuário
            new_level: Novo nível de permissão
            promoted_by: ID do admin que promoveu

        Returns:
            UseCaseResult: Resultado da operação
        """
        try:
            logger.info(f"Promovendo usuário {user_id} para {new_level.value}")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                return UseCaseResult(
                    success=False,
                    message="Usuário não encontrado"
                )

            # Busca admin que está promovendo
            admin = await self.user_repository.find_by_telegram_id(promoted_by)

            if not admin:
                return UseCaseResult(
                    success=False,
                    message="Administrador não encontrado"
                )

            # Valida se admin pode fazer essa promoção
            # (Aqui você precisaria ter as permissões atuais salvas)
            # Por simplificação, assumimos que admins podem promover até MODERATOR

            if new_level in [PermissionLevel.ADMIN, PermissionLevel.OWNER]:
                return UseCaseResult(
                    success=False,
                    message="Você não tem permissão para essa promoção"
                )

            # Publica evento de promoção
            from ...domain.events.user_events import UserPromotedEvent

            await self.event_bus.publish(
                UserPromotedEvent(
                    aggregate_id=user.id.value,
                    user_id=user.id,
                    new_level=new_level,
                    promoted_by=promoted_by,
                    promoted_at=datetime.now()
                )
            )

            logger.info(f"Usuário {user_id} promovido com sucesso")

            return UseCaseResult(
                success=True,
                message=f"Usuário promovido para {new_level.value} com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao promover usuário: {e}")
            return UseCaseResult(
                success=False,
                message="Erro ao promover usuário"
            )