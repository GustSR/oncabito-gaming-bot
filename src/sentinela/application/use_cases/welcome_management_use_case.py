"""
Welcome Management Use Case.

Gerencia o processo de boas-vindas de novos membros,
incluindo mensagens, aceitação de regras e concessão de acesso.
"""

import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.repositories.user_repository import UserRepository
from ...domain.repositories.group_member_repository import GroupMemberRepository
from ...domain.value_objects.welcome_message import WelcomeMessage, WelcomeMessageType
from ...domain.value_objects.identifiers import UserId
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class WelcomeResult:
    """Resultado de operação de boas-vindas."""

    success: bool
    message: str
    welcome_message: Optional[WelcomeMessage] = None
    rules_message: Optional[WelcomeMessage] = None
    user_id: Optional[int] = None


@dataclass
class RulesAcceptanceResult:
    """Resultado de aceitação de regras."""

    success: bool
    message: str
    access_granted: bool
    notification_text: str
    confirmation_message: Optional[WelcomeMessage] = None


class WelcomeManagementUseCase(UseCase):
    """
    Use Case para gerenciamento de boas-vindas.

    Coordena processo completo de onboarding de novos membros:
    - Envio de mensagens de boas-vindas
    - Gerenciamento de aceitação de regras
    - Concessão de acesso após aceitação
    - Remoção de membros que não aceitaram regras
    """

    def __init__(
        self,
        user_repository: UserRepository,
        member_repository: GroupMemberRepository,
        event_bus: EventBus,
        group_id: int,
        welcome_topic_id: Optional[int] = None,
        rules_topic_id: Optional[int] = None,
        rules_acceptance_hours: int = 24
    ):
        """
        Inicializa o use case.

        Args:
            user_repository: Repositório de usuários
            member_repository: Repositório de membros
            event_bus: Event bus para publicar eventos
            group_id: ID do grupo no Telegram
            welcome_topic_id: ID do tópico de boas-vindas (opcional)
            rules_topic_id: ID do tópico de regras (opcional)
            rules_acceptance_hours: Horas para aceitar regras (padrão 24h)
        """
        self.user_repository = user_repository
        self.member_repository = member_repository
        self.event_bus = event_bus
        self.group_id = group_id
        self.welcome_topic_id = welcome_topic_id
        self.rules_topic_id = rules_topic_id
        self.rules_acceptance_hours = rules_acceptance_hours

    async def handle_new_member(
        self,
        user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str] = None
    ) -> WelcomeResult:
        """
        Processa entrada de novo membro no grupo.

        Args:
            user_id: ID do usuário no Telegram
            username: Nome de usuário
            first_name: Primeiro nome
            last_name: Sobrenome (opcional)

        Returns:
            WelcomeResult: Resultado com mensagens a serem enviadas
        """
        try:
            logger.info(f"Processando novo membro: {username} (ID: {user_id})")

            # Marca usuário como pendente de aceitar regras
            await self._mark_pending_rules_acceptance(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )

            # Cria mensagem de boas-vindas
            welcome_msg = WelcomeMessage.create_initial_welcome(
                welcome_topic_id=self.welcome_topic_id
            )

            # Cria mensagem de lembrete de regras (se configurado)
            rules_msg = None
            if self.rules_topic_id:
                rules_msg = WelcomeMessage.create_rules_reminder(
                    rules_topic_id=self.rules_topic_id,
                    user_id=user_id
                )

            # Publica evento para envio de mensagens
            from ...domain.events.user_events import NewMemberJoinedEvent

            await self.event_bus.publish(
                NewMemberJoinedEvent(
                    aggregate_id=str(user_id),
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    joined_at=datetime.now()
                )
            )

            logger.info(f"Novo membro {username} processado com sucesso")

            return WelcomeResult(
                success=True,
                message="Mensagens de boas-vindas preparadas",
                welcome_message=welcome_msg,
                rules_message=rules_msg,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Erro ao processar novo membro {user_id}: {e}")
            return WelcomeResult(
                success=False,
                message=f"Erro ao processar novo membro: {str(e)}"
            )

    async def accept_rules(
        self,
        user_id: int,
        username: str
    ) -> RulesAcceptanceResult:
        """
        Processa aceitação de regras por um usuário.

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            RulesAcceptanceResult: Resultado da aceitação
        """
        try:
            logger.info(f"Processando aceitação de regras de {username} (ID: {user_id})")

            # Busca usuário
            user = await self.user_repository.find_by_telegram_id(user_id)

            if not user:
                return RulesAcceptanceResult(
                    success=False,
                    message="Usuário não encontrado",
                    access_granted=False,
                    notification_text=WelcomeMessage.create_unauthorized_button()
                )

            # Marca regras como aceitas
            user.mark_rules_accepted()
            await self.user_repository.save(user)

            # Tenta conceder acesso gaming
            access_granted = await self._try_grant_gaming_access(user_id, username)

            # Cria mensagem de confirmação
            confirmation_msg = WelcomeMessage.create_rules_accepted()

            # Define texto de notificação
            if access_granted:
                notification_text = WelcomeMessage.create_access_granted()
            else:
                notification_text = WelcomeMessage.create_access_pending()

            # Publica evento
            from ...domain.events.user_events import RulesAcceptedEvent

            await self.event_bus.publish(
                RulesAcceptedEvent(
                    aggregate_id=str(user_id),
                    user_id=user_id,
                    username=username,
                    access_granted=access_granted,
                    accepted_at=datetime.now()
                )
            )

            logger.info(f"Regras aceitas por {username}. Acesso: {access_granted}")

            return RulesAcceptanceResult(
                success=True,
                message="Regras aceitas com sucesso",
                access_granted=access_granted,
                notification_text=notification_text,
                confirmation_message=confirmation_msg
            )

        except Exception as e:
            logger.error(f"Erro ao processar aceitação de regras de {user_id}: {e}")
            return RulesAcceptanceResult(
                success=False,
                message=f"Erro ao processar aceitação: {str(e)}",
                access_granted=False,
                notification_text="❌ Erro ao processar sua aceitação."
            )

    async def check_expired_rules_acceptance(self) -> UseCaseResult:
        """
        Verifica e processa usuários que não aceitaram regras no prazo.

        Returns:
            UseCaseResult: Resultado da verificação
        """
        try:
            logger.info("Verificando usuários com aceitação de regras expirada")

            # Busca usuários não verificados há mais de X horas
            unverified = await self.member_repository.find_unverified_members()

            expired_count = 0
            removed_users = []

            for member in unverified:
                # Verifica se expirou prazo
                if self._is_rules_acceptance_expired(member.joined_at):
                    # Remove do grupo
                    result = await self._remove_member_for_no_rules(
                        member.telegram_id,
                        member.username or member.first_name
                    )

                    if result.success:
                        expired_count += 1
                        removed_users.append(member.username or member.first_name)

            logger.info(f"Verificação concluída: {expired_count} usuários removidos")

            return UseCaseResult(
                success=True,
                message=f"Verificação concluída: {expired_count} usuários removidos",
                data={
                    'expired_count': expired_count,
                    'removed_users': removed_users
                }
            )

        except Exception as e:
            logger.error(f"Erro ao verificar regras expiradas: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao verificar regras expiradas: {str(e)}"
            )

    # Private helper methods

    async def _mark_pending_rules_acceptance(
        self,
        user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str]
    ) -> None:
        """Marca usuário como pendente de aceitar regras."""
        # Busca ou cria usuário
        user = await self.user_repository.find_by_telegram_id(user_id)

        if not user:
            from ...domain.entities.user import User

            user = User(
                id=UserId(user_id),
                telegram_id=user_id,
                telegram_username=username,
                cpf=None,
                is_verified=False,
                is_banned=False
            )

        # Marca como pendente (não verificado)
        user.is_verified = False
        await self.user_repository.save(user)

        logger.info(f"Usuário {username} marcado como pendente de regras")

    async def _try_grant_gaming_access(
        self,
        user_id: int,
        username: str
    ) -> bool:
        """
        Tenta conceder acesso gaming ao usuário.

        Args:
            user_id: ID do usuário
            username: Nome do usuário

        Returns:
            bool: True se acesso foi concedido
        """
        try:
            # Publica evento para concessão de acesso
            from ...domain.events.user_events import GamingAccessRequestedEvent

            await self.event_bus.publish(
                GamingAccessRequestedEvent(
                    aggregate_id=str(user_id),
                    user_id=user_id,
                    username=username,
                    requested_at=datetime.now()
                )
            )

            # Por enquanto retorna True (handler resolverá)
            return True

        except Exception as e:
            logger.error(f"Erro ao tentar conceder acesso gaming: {e}")
            return False

    async def _remove_member_for_no_rules(
        self,
        user_id: int,
        username: str
    ) -> UseCaseResult:
        """Remove membro que não aceitou regras."""
        try:
            # Publica evento de remoção
            from ...domain.events.user_events import UserBanned

            await self.event_bus.publish(
                UserBanned(
                    aggregate_id=str(user_id),
                    user_id=user_id,
                    username=username,
                    reason="Não aceitou regras em 24 horas",
                    banned_by="system",
                    ban_date=datetime.now()
                )
            )

            logger.info(f"Usuário {username} removido por não aceitar regras")

            return UseCaseResult(
                success=True,
                message="Usuário removido"
            )

        except Exception as e:
            logger.error(f"Erro ao remover usuário {user_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao remover: {str(e)}"
            )

    def _is_rules_acceptance_expired(
        self,
        joined_at: Optional[datetime]
    ) -> bool:
        """
        Verifica se prazo para aceitar regras expirou.

        Args:
            joined_at: Data de entrada

        Returns:
            bool: True se expirou
        """
        if not joined_at:
            return False

        expiry_time = joined_at + timedelta(hours=self.rules_acceptance_hours)
        return datetime.now() > expiry_time
