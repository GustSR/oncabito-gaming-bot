"""
Event Handlers para eventos relacionados a usuários.

Processa eventos de domínio para implementar funcionalidades
como welcome messages, estatísticas e compliance.
"""

import asyncio
import logging
from typing import Type

from ..event_bus import EventHandler, DomainEvent
from ....domain.events.user_events import (
    UserRegistered,
    UserBanned,
    UserUnbanned,
    CPFValidated
)

logger = logging.getLogger(__name__)


class UserRegisteredHandler(EventHandler):
    """
    Handler para evento de usuário registrado.

    Responsabilidades:
    - Mensagem de boas-vindas
    - Configuração inicial do usuário
    - Log de novos registros
    - Métricas de crescimento
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return UserRegistered

    async def handle(self, event: UserRegistered) -> None:
        """
        Processa evento de usuário registrado.

        Args:
            event: Evento de usuário registrado
        """
        logger.info(
            f"🎉 NOVO USUÁRIO: {event.username} (ID: {event.user_id}) "
            f"registrado em {event.registration_date.strftime('%d/%m/%Y %H:%M')}"
        )

        # Envia mensagem de boas-vindas
        await self._send_welcome_message(event)

        # Configura perfil inicial
        await self._setup_initial_profile(event)

        # Atualiza métricas
        await self._update_growth_metrics(event)

    async def _send_welcome_message(self, event: UserRegistered) -> None:
        """
        Envia mensagem de boas-vindas para novo usuário.

        Args:
            event: Evento de usuário registrado
        """
        try:
            welcome_msg = (
                f"🎮 Bem-vindo à OnCabo Gaming, {event.username}!\n\n"
                f"🚀 Seu cadastro foi realizado com sucesso!\n"
                f"📞 Use /suporte para abrir tickets de atendimento\n"
                f"📊 Use /status para verificar conexão\n\n"
                f"🎯 Estamos aqui para oferecer a melhor experiência gaming!"
            )

            logger.info(
                f"💬 WELCOME: Mensagem de boas-vindas enviada para {event.username}"
            )

            # Simula envio da mensagem
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Erro ao enviar welcome message para usuário {event.user_id}: {e}")

    async def _setup_initial_profile(self, event: UserRegistered) -> None:
        """
        Configura perfil inicial do usuário.

        Args:
            event: Evento de usuário registrado
        """
        try:
            logger.debug(
                f"⚙️ SETUP: Configurando perfil inicial para {event.username}"
            )

            # Em produção, configuraria preferências padrão, etc.

        except Exception as e:
            logger.error(f"Erro ao configurar perfil para usuário {event.user_id}: {e}")

    async def _update_growth_metrics(self, event: UserRegistered) -> None:
        """
        Atualiza métricas de crescimento.

        Args:
            event: Evento de usuário registrado
        """
        try:
            logger.debug(
                f"📈 MÉTRICAS: Novo registro contabilizado - "
                f"Total de usuários incrementado"
            )

            # Em produção, atualizaria dashboard de métricas

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas para usuário {event.user_id}: {e}")


class UserBannedHandler(EventHandler):
    """
    Handler para evento de usuário banido.

    Responsabilidades:
    - Log de segurança
    - Notificação para administradores
    - Limpeza de sessões ativas
    - Auditoria de compliance
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return UserBanned

    async def handle(self, event: UserBanned) -> None:
        """
        Processa evento de usuário banido.

        Args:
            event: Evento de usuário banido
        """
        logger.warning(
            f"🚫 USUÁRIO BANIDO: {event.username} (ID: {event.user_id}) "
            f"- Motivo: {event.reason} - Admin: {event.banned_by}"
        )

        # Notifica administradores
        await self._notify_admins_ban(event)

        # Limpa sessões ativas
        await self._cleanup_user_sessions(event)

        # Log de segurança
        await self._security_audit_log(event)

    async def _notify_admins_ban(self, event: UserBanned) -> None:
        """
        Notifica administradores sobre banimento.

        Args:
            event: Evento de usuário banido
        """
        try:
            logger.info(
                f"📢 ADMIN ALERT: Usuário {event.username} banido "
                f"por {event.banned_by} - Motivo: {event.reason}"
            )

            # Em produção, enviaria notificação para canal de admins

        except Exception as e:
            logger.error(f"Erro ao notificar admins sobre ban de usuário {event.user_id}: {e}")

    async def _cleanup_user_sessions(self, event: UserBanned) -> None:
        """
        Limpa sessões ativas do usuário banido.

        Args:
            event: Evento de usuário banido
        """
        try:
            logger.debug(
                f"🧹 CLEANUP: Limpando sessões ativas para {event.username}"
            )

            # Em produção, removeria conversations ativas, cache, etc.

        except Exception as e:
            logger.error(f"Erro ao limpar sessões para usuário {event.user_id}: {e}")

    async def _security_audit_log(self, event: UserBanned) -> None:
        """
        Registra evento para auditoria de segurança.

        Args:
            event: Evento de usuário banido
        """
        try:
            logger.info(
                f"🔒 SECURITY AUDIT: Ban registrado - "
                f"User: {event.user_id}, Admin: {event.banned_by}, "
                f"Timestamp: {event.ban_date.isoformat()}"
            )

            # Em produção, salvaria em sistema de auditoria de segurança

        except Exception as e:
            logger.error(f"Erro no security audit para usuário {event.user_id}: {e}")


class UserUnbannedHandler(EventHandler):
    """
    Handler para evento de usuário desbanido.

    Responsabilidades:
    - Restauração de acesso
    - Notificação de reativação
    - Log de auditoria
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return UserUnbanned

    async def handle(self, event: UserUnbanned) -> None:
        """
        Processa evento de usuário desbanido.

        Args:
            event: Evento de usuário desbanido
        """
        logger.info(
            f"✅ USUÁRIO DESBANIDO: {event.username} (ID: {event.user_id}) "
            f"reativado por {event.unbanned_by}"
        )

        # Restaura acesso do usuário
        await self._restore_user_access(event)

        # Envia notificação de reativação
        await self._send_reactivation_notice(event)

        # Log de auditoria
        await self._audit_unban(event)

    async def _restore_user_access(self, event: UserUnbanned) -> None:
        """
        Restaura acesso completo do usuário.

        Args:
            event: Evento de usuário desbanido
        """
        try:
            logger.debug(
                f"🔓 ACESSO RESTAURADO: {event.username} pode usar o sistema novamente"
            )

            # Em produção, removeria restrições, restauraria permissões, etc.

        except Exception as e:
            logger.error(f"Erro ao restaurar acesso para usuário {event.user_id}: {e}")

    async def _send_reactivation_notice(self, event: UserUnbanned) -> None:
        """
        Envia notificação de reativação.

        Args:
            event: Evento de usuário desbanido
        """
        try:
            reactivation_msg = (
                f"🎉 Olá {event.username}!\n\n"
                f"✅ Seu acesso foi reativado!\n"
                f"🎮 Você pode voltar a usar todos os serviços OnCabo Gaming.\n\n"
                f"📞 Em caso de dúvidas, use /suporte"
            )

            logger.info(
                f"💬 REATIVAÇÃO: Notificação enviada para {event.username}"
            )

        except Exception as e:
            logger.error(f"Erro ao enviar notificação de reativação para usuário {event.user_id}: {e}")

    async def _audit_unban(self, event: UserUnbanned) -> None:
        """
        Registra unban para auditoria.

        Args:
            event: Evento de usuário desbanido
        """
        try:
            logger.info(
                f"📋 AUDIT: Unban registrado - "
                f"User: {event.user_id}, Admin: {event.unbanned_by}, "
                f"Timestamp: {event.unban_date.isoformat()}"
            )

        except Exception as e:
            logger.error(f"Erro no audit de unban para usuário {event.user_id}: {e}")


class CPFValidatedHandler(EventHandler):
    """
    Handler para evento de CPF validado.

    Responsabilidades:
    - Log de compliance
    - Ativação de funcionalidades premium
    - Métricas de verificação
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return CPFValidated

    async def handle(self, event: CPFValidated) -> None:
        """
        Processa evento de CPF validado.

        Args:
            event: Evento de CPF validado
        """
        # CPF mascarado para logs (LGPD compliance)
        masked_cpf = f"***.***.***-{event.cpf_number[-2:]}"

        logger.info(
            f"✅ CPF VALIDADO: Usuário {event.username} (ID: {event.user_id}) "
            f"- CPF: {masked_cpf} - Válido: {event.is_valid}"
        )

        if event.is_valid:
            await self._handle_valid_cpf(event)
        else:
            await self._handle_invalid_cpf(event)

        # Métricas de validação
        await self._update_validation_metrics(event)

    async def _handle_valid_cpf(self, event: CPFValidated) -> None:
        """
        Processa CPF válido.

        Args:
            event: Evento de CPF validado
        """
        try:
            logger.info(
                f"🎉 CPF VÁLIDO: Ativando funcionalidades premium para {event.username}"
            )

            # Em produção, ativaria features premium, aumentaria limites, etc.

        except Exception as e:
            logger.error(f"Erro ao processar CPF válido para usuário {event.user_id}: {e}")

    async def _handle_invalid_cpf(self, event: CPFValidated) -> None:
        """
        Processa CPF inválido.

        Args:
            event: Evento de CPF validado
        """
        try:
            logger.warning(
                f"❌ CPF INVÁLIDO: Mantendo restrições para {event.username}"
            )

            # Em produção, manteria limitações, enviaria orientações, etc.

        except Exception as e:
            logger.error(f"Erro ao processar CPF inválido para usuário {event.user_id}: {e}")

    async def _update_validation_metrics(self, event: CPFValidated) -> None:
        """
        Atualiza métricas de validação.

        Args:
            event: Evento de CPF validado
        """
        try:
            status = "válido" if event.is_valid else "inválido"
            logger.debug(
                f"📊 MÉTRICAS: Validação de CPF {status} contabilizada"
            )

            # Em produção, atualizaria dashboard de compliance

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas de CPF para usuário {event.user_id}: {e}")


class UserActivityAuditHandler(EventHandler):
    """
    Handler global para auditoria de atividades de usuário.

    Responsabilidades:
    - Log detalhado de compliance
    - Métricas de engajamento
    - Análise de comportamento
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        # Handler global para todos os eventos
        return DomainEvent

    async def handle(self, event: DomainEvent) -> None:
        """
        Processa qualquer evento para auditoria de usuário.

        Args:
            event: Qualquer evento de domínio
        """
        # Só processa eventos relacionados a usuários
        if not any(keyword in event.__class__.__name__ for keyword in ['User', 'CPF']):
            return

        logger.debug(
            f"👤 USER ACTIVITY: {event.__class__.__name__} "
            f"em {event.occurred_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Em produção, salvaria para análise de comportamento
        await self._save_activity_log(event)

    async def _save_activity_log(self, event: DomainEvent) -> None:
        """
        Salva log de atividade do usuário.

        Args:
            event: Evento a ser registrado
        """
        try:
            # Em produção, salvaria em sistema de analytics
            logger.debug(f"📊 ACTIVITY LOG: {event.__class__.__name__} registrado")

        except Exception as e:
            logger.error(f"Erro ao salvar activity log: {e}")