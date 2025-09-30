"""
Invite Management Use Case.

Gerencia criação, revogação e tracking de links de convite.
"""

import logging
import time
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.entities.invite_link import InviteLink, InviteLinkStatus
from ...domain.value_objects.identifiers import UserId
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class InviteCreationResult:
    """Resultado de criação de convite."""

    success: bool
    message: str
    invite_link: Optional[InviteLink] = None
    invite_url: Optional[str] = None
    expires_in: Optional[timedelta] = None


class InviteManagementUseCase(UseCase):
    """
    Use Case para gerenciamento de convites.

    Coordena criação, tracking e revogação de links de convite
    para o grupo do Telegram.
    """

    def __init__(
        self,
        event_bus: EventBus,
        group_id: int,
        default_expire_time: int = 1800,  # 30 minutos
        default_member_limit: int = 1
    ):
        """
        Inicializa o use case.

        Args:
            event_bus: Event bus para publicar eventos
            group_id: ID do grupo no Telegram
            default_expire_time: Tempo de expiração padrão (segundos)
            default_member_limit: Limite de membros padrão
        """
        self.event_bus = event_bus
        self.group_id = group_id
        self.default_expire_time = default_expire_time
        self.default_member_limit = default_member_limit

    async def create_invite_link(
        self,
        for_user_id: int,
        for_username: str,
        created_by_user_id: int,
        expire_time_seconds: Optional[int] = None,
        member_limit: Optional[int] = None
    ) -> InviteCreationResult:
        """
        Cria novo link de convite personalizado.

        Args:
            for_user_id: ID do usuário para quem o link é criado
            for_username: Nome do usuário
            created_by_user_id: ID de quem está criando
            expire_time_seconds: Tempo de expiração (segundos)
            member_limit: Limite de membros

        Returns:
            InviteCreationResult: Resultado da criação
        """
        try:
            logger.info(f"Criando link de convite para {for_username} (ID: {for_user_id})")

            # Define parâmetros
            expire_seconds = expire_time_seconds or self.default_expire_time
            limit = member_limit or self.default_member_limit

            # Calcula data de expiração
            expire_date = datetime.now() + timedelta(seconds=expire_seconds)
            expire_timestamp = int(time.time()) + expire_seconds

            # Nome do link
            link_name = f"Acesso {for_username} - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

            # Publica evento para criar link no Telegram
            from ...domain.events.user_events import InviteLinkRequestedEvent

            invite_data = {
                'for_user_id': for_user_id,
                'for_username': for_username,
                'created_by': created_by_user_id,
                'name': link_name,
                'expire_timestamp': expire_timestamp,
                'member_limit': limit,
                'group_id': self.group_id
            }

            await self.event_bus.publish(
                InviteLinkRequestedEvent(
                    aggregate_id=str(for_user_id),
                    user_id=UserId(for_user_id),
                    invite_data=invite_data,
                    created_at=datetime.now()
                )
            )

            # Cria entidade do link
            invite_link = InviteLink(
                id=UserId(int(time.time())),  # ID temporário baseado em timestamp
                created_for_user=UserId(for_user_id),
                created_by=UserId(created_by_user_id),
                invite_url="pending",  # Será preenchido pelo handler
                name=link_name,
                expire_date=expire_date,
                member_limit=limit,
                creates_join_request=False,
                status=InviteLinkStatus.ACTIVE
            )

            logger.info(f"Link de convite criado com sucesso para {for_username}")

            # Formata mensagem de sucesso
            time_formatted = self._format_expiry_time(expire_seconds)

            return InviteCreationResult(
                success=True,
                message=(
                    f"✅ **Link de convite criado!**\n\n"
                    f"👤 **Para:** {for_username}\n"
                    f"⏰ **Expira em:** {time_formatted}\n"
                    f"👥 **Limite:** {limit} pessoa(s)\n\n"
                    f"📋 **Instruções:**\n"
                    f"• O link é válido apenas para este usuário\n"
                    f"• Após o uso ou expiração, será automaticamente revogado\n"
                    f"• Use `/revoke_invite` para revogar manualmente"
                ),
                invite_link=invite_link,
                expires_in=timedelta(seconds=expire_seconds)
            )

        except Exception as e:
            logger.error(f"Erro ao criar link de convite: {e}")
            return InviteCreationResult(
                success=False,
                message=f"❌ Erro ao criar link: {str(e)}"
            )

    async def revoke_invite_link(
        self,
        invite_url: str,
        reason: str = "Manual revocation",
        revoked_by: Optional[int] = None
    ) -> UseCaseResult:
        """
        Revoga um link de convite específico.

        Args:
            invite_url: URL do link
            reason: Motivo da revogação
            revoked_by: ID de quem revogou

        Returns:
            UseCaseResult: Resultado da operação
        """
        try:
            logger.info(f"Revogando link de convite: {invite_url}")

            # Publica evento para revogar no Telegram
            from ...domain.events.user_events import InviteLinkRevokedEvent

            await self.event_bus.publish(
                InviteLinkRevokedEvent(
                    aggregate_id=invite_url,
                    invite_url=invite_url,
                    reason=reason,
                    revoked_by=revoked_by,
                    revoked_at=datetime.now()
                )
            )

            logger.info("Link de convite revogado com sucesso")

            return UseCaseResult(
                success=True,
                message="✅ Link de convite revogado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao revogar link: {e}")
            return UseCaseResult(
                success=False,
                message=f"❌ Erro ao revogar link: {str(e)}"
            )

    async def create_verification_invite(
        self,
        user_id: int,
        username: str,
        cpf_verified: bool = True
    ) -> InviteCreationResult:
        """
        Cria link de convite após verificação de CPF.

        Args:
            user_id: ID do usuário
            username: Nome do usuário
            cpf_verified: Se CPF foi verificado

        Returns:
            InviteCreationResult: Resultado da criação
        """
        try:
            logger.info(f"Criando link de verificação para {username}")

            if not cpf_verified:
                return InviteCreationResult(
                    success=False,
                    message="❌ CPF não verificado. Verifique seu CPF primeiro."
                )

            # Cria link com tempo estendido (1 hora) para verificados
            return await self.create_invite_link(
                for_user_id=user_id,
                for_username=username,
                created_by_user_id=0,  # Sistema
                expire_time_seconds=3600,  # 1 hora
                member_limit=1
            )

        except Exception as e:
            logger.error(f"Erro ao criar link de verificação: {e}")
            return InviteCreationResult(
                success=False,
                message=f"❌ Erro ao criar link: {str(e)}"
            )

    async def cleanup_expired_invites(self) -> UseCaseResult:
        """
        Remove links de convite expirados.

        Returns:
            UseCaseResult: Resultado da limpeza
        """
        try:
            logger.info("Iniciando limpeza de convites expirados")

            # Publica evento para cleanup
            from ...domain.events.user_events import InviteCleanupRequestedEvent

            await self.event_bus.publish(
                InviteCleanupRequestedEvent(
                    aggregate_id="cleanup",
                    requested_at=datetime.now()
                )
            )

            logger.info("Limpeza de convites iniciada")

            return UseCaseResult(
                success=True,
                message="✅ Limpeza de convites expirados iniciada"
            )

        except Exception as e:
            logger.error(f"Erro na limpeza de convites: {e}")
            return UseCaseResult(
                success=False,
                message=f"❌ Erro na limpeza: {str(e)}"
            )

    def _format_expiry_time(self, seconds: int) -> str:
        """
        Formata tempo de expiração para exibição.

        Args:
            seconds: Segundos até expiração

        Returns:
            str: Tempo formatado
        """
        if seconds < 60:
            return f"{seconds} segundos"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minuto(s)"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hora(s)"
        else:
            days = seconds // 86400
            return f"{days} dia(s)"