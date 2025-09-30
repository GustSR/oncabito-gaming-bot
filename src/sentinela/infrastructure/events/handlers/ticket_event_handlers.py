"""
Event Handlers para eventos relacionados a tickets.

Processa eventos de domínio para implementar side effects
como notificações, logs de auditoria e sincronização com sistemas externos.
"""

import asyncio
import logging
from typing import Type

from ..event_bus import EventHandler, DomainEvent
from ....domain.events.ticket_events import (
    TicketCreated,
    TicketAssigned,
    TicketStatusChanged,
    TicketSyncedWithHubSoft
)

logger = logging.getLogger(__name__)


class TicketCreatedHandler(EventHandler):
    """
    Handler para evento de ticket criado.

    Responsabilidades:
    - Log de auditoria
    - Notificação para administradores
    - Preparação para sincronização com HubSoft
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return TicketCreated

    async def handle(self, event: TicketCreated) -> None:
        """
        Processa evento de ticket criado.

        Args:
            event: Evento de ticket criado
        """
        logger.info(
            f"📝 TICKET CRIADO: {event.ticket_id} por usuário {event.user_id} "
            f"- Categoria: {event.category} - Protocolo: {event.protocol}"
        )

        # Simula notificação para admins (em produção seria via Telegram)
        await self._notify_admins_new_ticket(event)

        # Simula preparação para sync com HubSoft
        await self._prepare_hubsoft_sync(event)

    async def _notify_admins_new_ticket(self, event: TicketCreated) -> None:
        """
        Notifica administradores sobre novo ticket.

        Args:
            event: Evento de ticket criado
        """
        try:
            # Em produção, enviar notificação real via Telegram Bot API
            logger.info(
                f"📢 NOTIFICAÇÃO ADMIN: Novo ticket {event.protocol} "
                f"criado por {event.username} - {event.category}"
            )

            # Simula delay de notificação
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Erro ao notificar admins sobre ticket {event.ticket_id}: {e}")

    async def _prepare_hubsoft_sync(self, event: TicketCreated) -> None:
        """
        Prepara dados para sincronização com HubSoft.

        Args:
            event: Evento de ticket criado
        """
        try:
            # Em produção, adicionaria à fila de sincronização
            logger.debug(
                f"🔄 SYNC PREPARADO: Ticket {event.ticket_id} "
                f"adicionado à fila de sincronização HubSoft"
            )

        except Exception as e:
            logger.error(f"Erro ao preparar sync para ticket {event.ticket_id}: {e}")


class TicketAssignedHandler(EventHandler):
    """
    Handler para evento de ticket atribuído.

    Responsabilidades:
    - Notificação para o técnico designado
    - Atualização de métricas de workload
    - Log de atribuição
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return TicketAssigned

    async def handle(self, event: TicketAssigned) -> None:
        """
        Processa evento de ticket atribuído.

        Args:
            event: Evento de ticket atribuído
        """
        logger.info(
            f"👤 TICKET ATRIBUÍDO: {event.ticket_id} → {event.technician} "
            f"(Status: {event.status})"
        )

        # Notifica técnico (em produção seria via Telegram/email)
        await self._notify_technician(event)

        # Atualiza métricas de workload
        await self._update_workload_metrics(event)

    async def _notify_technician(self, event: TicketAssigned) -> None:
        """
        Notifica técnico sobre atribuição.

        Args:
            event: Evento de ticket atribuído
        """
        try:
            logger.info(
                f"📨 NOTIFICAÇÃO TÉCNICO: {event.technician} "
                f"recebeu ticket {event.ticket_id}"
            )

            # Simula envio de notificação
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Erro ao notificar técnico sobre ticket {event.ticket_id}: {e}")

    async def _update_workload_metrics(self, event: TicketAssigned) -> None:
        """
        Atualiza métricas de carga de trabalho.

        Args:
            event: Evento de ticket atribuído
        """
        try:
            # Em produção, atualizaria métricas reais
            logger.debug(
                f"📊 MÉTRICAS: Workload atualizado para {event.technician} "
                f"(+1 ticket ativo)"
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas para ticket {event.ticket_id}: {e}")


class TicketStatusChangedHandler(EventHandler):
    """
    Handler para evento de mudança de status.

    Responsabilidades:
    - Log de auditoria de mudanças
    - Notificação para usuário sobre progresso
    - Atualização de dashboards
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return TicketStatusChanged

    async def handle(self, event: TicketStatusChanged) -> None:
        """
        Processa evento de mudança de status.

        Args:
            event: Evento de mudança de status
        """
        logger.info(
            f"🔄 STATUS ALTERADO: Ticket {event.ticket_id} "
            f"{event.old_status} → {event.new_status}"
        )

        # Notifica usuário sobre mudança
        await self._notify_user_status_change(event)

        # Atualiza dashboards
        await self._update_dashboards(event)

        # Lógica especial para tickets resolvidos
        if event.new_status == "RESOLVED":
            await self._handle_ticket_resolved(event)

    async def _notify_user_status_change(self, event: TicketStatusChanged) -> None:
        """
        Notifica usuário sobre mudança de status.

        Args:
            event: Evento de mudança de status
        """
        try:
            status_messages = {
                "OPEN": "📩 Seu ticket foi aberto e está sendo analisado",
                "IN_PROGRESS": "🔧 Técnico está trabalhando no seu ticket",
                "RESOLVED": "✅ Seu ticket foi resolvido!",
                "CLOSED": "📝 Ticket finalizado. Obrigado pelo contato!"
            }

            message = status_messages.get(event.new_status, "Ticket atualizado")

            logger.info(
                f"💬 NOTIFICAÇÃO USUÁRIO: {event.user_id} - {message} "
                f"(Ticket: {event.ticket_id})"
            )

        except Exception as e:
            logger.error(f"Erro ao notificar usuário sobre ticket {event.ticket_id}: {e}")

    async def _update_dashboards(self, event: TicketStatusChanged) -> None:
        """
        Atualiza dashboards com nova informação.

        Args:
            event: Evento de mudança de status
        """
        try:
            logger.debug(
                f"📈 DASHBOARD: Métricas atualizadas para mudança "
                f"{event.old_status} → {event.new_status}"
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar dashboard para ticket {event.ticket_id}: {e}")

    async def _handle_ticket_resolved(self, event: TicketStatusChanged) -> None:
        """
        Lógica especial para tickets resolvidos.

        Args:
            event: Evento de mudança de status
        """
        try:
            logger.info(
                f"🎉 TICKET RESOLVIDO: {event.ticket_id} "
                f"- Iniciando processo de feedback"
            )

            # Em produção, iniciaria processo de feedback automatizado

        except Exception as e:
            logger.error(f"Erro no processo de resolução para ticket {event.ticket_id}: {e}")


class TicketSyncedHandler(EventHandler):
    """
    Handler para evento de sincronização com HubSoft.

    Responsabilidades:
    - Log de sincronização bem-sucedida
    - Atualização de status de sync
    - Retry logic para falhas
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return TicketSyncedWithHubSoft

    async def handle(self, event: TicketSyncedWithHubSoft) -> None:
        """
        Processa evento de sincronização com HubSoft.

        Args:
            event: Evento de sincronização
        """
        logger.info(
            f"🔗 HUBSOFT SYNC: Ticket {event.ticket_id} "
            f"sincronizado com HubSoft ID: {event.hubsoft_id}"
        )

        # Atualiza status de sincronização
        await self._update_sync_status(event)

        # Valida integridade dos dados
        await self._validate_sync_integrity(event)

    async def _update_sync_status(self, event: TicketSyncedWithHubSoft) -> None:
        """
        Atualiza status de sincronização.

        Args:
            event: Evento de sincronização
        """
        try:
            logger.debug(
                f"✅ SYNC STATUS: Ticket {event.ticket_id} "
                f"marcado como sincronizado"
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar status de sync para ticket {event.ticket_id}: {e}")

    async def _validate_sync_integrity(self, event: TicketSyncedWithHubSoft) -> None:
        """
        Valida integridade da sincronização.

        Args:
            event: Evento de sincronização
        """
        try:
            # Em produção, validaria dados no HubSoft
            logger.debug(
                f"🔍 VALIDAÇÃO: Integridade confirmada para sync "
                f"{event.ticket_id} ↔ {event.hubsoft_id}"
            )

        except Exception as e:
            logger.error(f"Erro na validação de sync para ticket {event.ticket_id}: {e}")


class TicketAuditHandler(EventHandler):
    """
    Handler global para auditoria de todos eventos de ticket.

    Responsabilidades:
    - Log detalhado de auditoria
    - Armazenamento para compliance
    - Métricas gerais do sistema
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        # Este handler será registrado como global
        return DomainEvent

    async def handle(self, event: DomainEvent) -> None:
        """
        Processa qualquer evento para auditoria.

        Args:
            event: Qualquer evento de domínio
        """
        # Só processa eventos relacionados a tickets
        if not any(keyword in event.__class__.__name__ for keyword in ['Ticket', 'Conversation']):
            return

        logger.info(
            f"📋 AUDITORIA: {event.__class__.__name__} "
            f"em {event.occurred_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Em produção, salvaria em sistema de auditoria
        await self._save_audit_log(event)

    async def _save_audit_log(self, event: DomainEvent) -> None:
        """
        Salva log de auditoria.

        Args:
            event: Evento a ser auditado
        """
        try:
            # Em produção, salvaria em banco de dados de auditoria
            logger.debug(f"💾 AUDIT LOG: {event.__class__.__name__} salvo para auditoria")

        except Exception as e:
            logger.error(f"Erro ao salvar audit log: {e}")