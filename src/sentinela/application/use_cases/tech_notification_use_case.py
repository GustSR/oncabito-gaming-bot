"""
Tech Notification Use Case.

Coordena envio de notificações técnicas para o canal
de monitoramento da equipe.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.services.notification_formatter_service import NotificationFormatterService
from ...domain.value_objects.notification_priority import (
    NotificationPriority,
    determine_notification_priority
)
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Resultado de envio de notificação."""

    success: bool
    message: str
    notification_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    channel_id: Optional[int] = None


class TechNotificationUseCase(UseCase):
    """
    Use Case para envio de notificações técnicas.

    Coordena a formatação e envio de notificações para
    o canal técnico baseado em prioridade e contexto.
    """

    def __init__(
        self,
        formatter_service: NotificationFormatterService,
        event_bus: EventBus,
        tech_channel_id: int
    ):
        """
        Inicializa o use case.

        Args:
            formatter_service: Serviço de formatação de notificações
            event_bus: Event bus para publicar eventos
            tech_channel_id: ID do canal técnico no Telegram
        """
        self.formatter_service = formatter_service
        self.event_bus = event_bus
        self.tech_channel_id = tech_channel_id

    async def notify_new_ticket(
        self,
        ticket_data: Dict[str, Any],
        user_data: Dict[str, Any],
        protocol: str
    ) -> NotificationResult:
        """
        Envia notificação sobre novo ticket criado.

        Args:
            ticket_data: Dados do ticket
            user_data: Dados do usuário/cliente
            protocol: Protocolo do atendimento

        Returns:
            NotificationResult: Resultado do envio
        """
        try:
            if not self.tech_channel_id:
                logger.warning(f"Canal técnico não configurado - notificação do ticket {protocol} não enviada")
                return NotificationResult(
                    success=False,
                    message="Canal técnico não configurado"
                )

            logger.info(f"Enviando notificação técnica para ticket {protocol}")

            # Determina prioridade
            priority = determine_notification_priority(
                urgency_level=ticket_data.get('urgency_level'),
                category=ticket_data.get('category'),
                has_attachments=bool(ticket_data.get('attachments'))
            )

            # Formata mensagem baseada na prioridade
            if priority == NotificationPriority.CRITICAL:
                message = self.formatter_service.format_critical_notification(
                    ticket_data,
                    user_data,
                    protocol
                )
            elif priority == NotificationPriority.HIGH:
                message = self.formatter_service.format_high_notification(
                    ticket_data,
                    user_data,
                    protocol
                )
            else:
                message = self.formatter_service.format_normal_notification(
                    ticket_data,
                    user_data,
                    protocol
                )

            # Publica evento para envio via Telegram
            from ...domain.events.ticket_events import TechNotificationRequiredEvent

            await self.event_bus.publish(
                TechNotificationRequiredEvent(
                    aggregate_id=protocol,
                    ticket_protocol=protocol,
                    priority=priority,
                    message=message,
                    channel_id=self.tech_channel_id,
                    created_at=datetime.now()
                )
            )

            logger.info(f"Notificação técnica publicada para ticket {protocol}")

            return NotificationResult(
                success=True,
                message="Notificação enviada com sucesso",
                notification_id=f"NOTIF_{protocol}_{int(datetime.now().timestamp())}",
                sent_at=datetime.now(),
                channel_id=self.tech_channel_id
            )

        except Exception as e:
            logger.error(f"Erro ao enviar notificação técnica para ticket {protocol}: {e}")
            return NotificationResult(
                success=False,
                message=f"Erro ao enviar notificação: {str(e)}"
            )

    async def notify_ticket_update(
        self,
        protocol: str,
        status: str,
        update_message: Optional[str] = None
    ) -> NotificationResult:
        """
        Envia notificação sobre atualização de ticket.

        Args:
            protocol: Protocolo do ticket
            status: Novo status do ticket
            update_message: Mensagem de atualização (opcional)

        Returns:
            NotificationResult: Resultado do envio
        """
        try:
            if not self.tech_channel_id:
                logger.warning(f"Canal técnico não configurado - notificação de update não enviada")
                return NotificationResult(
                    success=False,
                    message="Canal técnico não configurado"
                )

            logger.info(f"Enviando notificação de atualização para ticket {protocol}")

            # Formata mensagem
            message = self.formatter_service.format_update_notification(
                protocol,
                status,
                update_message
            )

            # Determina prioridade baseada no status
            priority = self._determine_update_priority(status)

            # Publica evento
            from ...domain.events.ticket_events import TechNotificationRequiredEvent

            await self.event_bus.publish(
                TechNotificationRequiredEvent(
                    aggregate_id=protocol,
                    ticket_protocol=protocol,
                    priority=priority,
                    message=message,
                    channel_id=self.tech_channel_id,
                    created_at=datetime.now()
                )
            )

            logger.info(f"Notificação de update publicada para ticket {protocol}")

            return NotificationResult(
                success=True,
                message="Notificação de atualização enviada",
                notification_id=f"UPDATE_{protocol}_{int(datetime.now().timestamp())}",
                sent_at=datetime.now(),
                channel_id=self.tech_channel_id
            )

        except Exception as e:
            logger.error(f"Erro ao enviar notificação de update: {e}")
            return NotificationResult(
                success=False,
                message=f"Erro ao enviar notificação: {str(e)}"
            )

    async def notify_verification_required(
        self,
        user_id: int,
        username: str,
        verification_type: str,
        details: Optional[str] = None
    ) -> NotificationResult:
        """
        Notifica que verificação manual é necessária.

        Args:
            user_id: ID do usuário
            username: Nome do usuário
            verification_type: Tipo de verificação necessária
            details: Detalhes adicionais (opcional)

        Returns:
            NotificationResult: Resultado do envio
        """
        try:
            if not self.tech_channel_id:
                logger.warning("Canal técnico não configurado")
                return NotificationResult(
                    success=False,
                    message="Canal técnico não configurado"
                )

            logger.info(f"Enviando notificação de verificação para usuário {user_id}")

            # Formata mensagem
            current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

            verification_types = {
                'cpf': '📋 Verificação de CPF',
                'permission': '🔐 Liberação de Acesso',
                'ticket': '🎫 Aprovação de Ticket',
                'ban': '🚫 Revisão de Banimento'
            }

            title = verification_types.get(verification_type, '⚠️ Verificação Manual')

            message = (
                f"⚠️ <b>VERIFICAÇÃO MANUAL NECESSÁRIA</b>\n\n"
                f"📋 <b>Tipo:</b> {title}\n"
                f"👤 <b>Usuário:</b> {username}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"🕒 <b>Horário:</b> {current_time}\n"
            )

            if details:
                message += f"\n📝 <b>Detalhes:</b>\n{details}\n"

            message += f"\n🔧 <b>Ação necessária:</b> Revisar e aprovar manualmente"

            # Publica evento
            from ...domain.events.user_events import AdminNotificationRequiredEvent
            from ...domain.value_objects.identifiers import UserId

            await self.event_bus.publish(
                AdminNotificationRequiredEvent(
                    aggregate_id=str(user_id),
                    user_id=UserId(user_id),
                    notification_type=verification_type,
                    message=message,
                    channel_id=self.tech_channel_id,
                    created_at=datetime.now()
                )
            )

            logger.info(f"Notificação de verificação publicada para usuário {user_id}")

            return NotificationResult(
                success=True,
                message="Notificação de verificação enviada",
                sent_at=datetime.now(),
                channel_id=self.tech_channel_id
            )

        except Exception as e:
            logger.error(f"Erro ao enviar notificação de verificação: {e}")
            return NotificationResult(
                success=False,
                message=f"Erro ao enviar notificação: {str(e)}"
            )

    async def notify_system_alert(
        self,
        alert_type: str,
        alert_message: str,
        severity: str = "medium"
    ) -> NotificationResult:
        """
        Envia alerta de sistema para o canal técnico.

        Args:
            alert_type: Tipo de alerta (error, warning, info)
            alert_message: Mensagem do alerta
            severity: Severidade (critical, high, medium, low)

        Returns:
            NotificationResult: Resultado do envio
        """
        try:
            if not self.tech_channel_id:
                logger.warning("Canal técnico não configurado")
                return NotificationResult(
                    success=False,
                    message="Canal técnico não configurado"
                )

            logger.info(f"Enviando alerta de sistema: {alert_type}")

            # Emojis por tipo de alerta
            alert_emojis = {
                'error': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️',
                'success': '✅'
            }

            emoji = alert_emojis.get(alert_type, '📢')
            current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

            message = (
                f"{emoji} <b>ALERTA DE SISTEMA</b>\n\n"
                f"📋 <b>Tipo:</b> {alert_type.upper()}\n"
                f"⚡ <b>Severidade:</b> {severity.upper()}\n"
                f"🕒 <b>Horário:</b> {current_time}\n\n"
                f"💬 <b>Mensagem:</b>\n{alert_message}"
            )

            # Determina prioridade
            severity_map = {
                'critical': NotificationPriority.CRITICAL,
                'high': NotificationPriority.HIGH,
                'medium': NotificationPriority.MEDIUM,
                'low': NotificationPriority.LOW
            }

            priority = severity_map.get(severity, NotificationPriority.MEDIUM)

            # Publica evento
            from ...domain.events.ticket_events import TechNotificationRequiredEvent

            await self.event_bus.publish(
                TechNotificationRequiredEvent(
                    aggregate_id=f"ALERT_{int(datetime.now().timestamp())}",
                    ticket_protocol=f"SYSTEM_ALERT_{alert_type}",
                    priority=priority,
                    message=message,
                    channel_id=self.tech_channel_id,
                    created_at=datetime.now()
                )
            )

            logger.info(f"Alerta de sistema publicado: {alert_type}")

            return NotificationResult(
                success=True,
                message="Alerta enviado com sucesso",
                sent_at=datetime.now(),
                channel_id=self.tech_channel_id
            )

        except Exception as e:
            logger.error(f"Erro ao enviar alerta de sistema: {e}")
            return NotificationResult(
                success=False,
                message=f"Erro ao enviar alerta: {str(e)}"
            )

    def _determine_update_priority(self, status: str) -> NotificationPriority:
        """Determina prioridade baseada no status do ticket."""
        critical_statuses = ['escalated', 'critical']
        high_statuses = ['in_progress', 'pending_client']
        low_statuses = ['resolved', 'closed']

        if status in critical_statuses:
            return NotificationPriority.CRITICAL

        if status in high_statuses:
            return NotificationPriority.HIGH

        if status in low_statuses:
            return NotificationPriority.LOW

        return NotificationPriority.MEDIUM