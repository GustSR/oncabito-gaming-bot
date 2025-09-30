"""
Notification Priority Value Object.

Define os níveis de prioridade para notificações técnicas.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import timedelta


class NotificationPriority(Enum):
    """Níveis de prioridade de notificações."""

    CRITICAL = "critical"    # 🚨 Crítico - Requer atenção imediata
    HIGH = "high"           # ⚠️ Alta - Importante, resposta rápida
    MEDIUM = "medium"       # 🔧 Média - Normal, resposta padrão
    LOW = "low"            # 💡 Baixa - Informativo
    INFO = "info"          # ℹ️ Info - Apenas informativo


@dataclass(frozen=True)
class NotificationSLA:
    """
    Define SLA (Service Level Agreement) para notificações.

    Attributes:
        priority: Nível de prioridade
        response_time: Tempo esperado de resposta
        emoji: Emoji representativo
        requires_acknowledgment: Se requer confirmação de leitura
    """

    priority: NotificationPriority
    response_time: timedelta
    emoji: str
    requires_acknowledgment: bool = False

    @classmethod
    def for_priority(cls, priority: NotificationPriority) -> 'NotificationSLA':
        """
        Cria SLA baseado na prioridade.

        Args:
            priority: Nível de prioridade

        Returns:
            NotificationSLA: Configuração de SLA
        """
        sla_config = {
            NotificationPriority.CRITICAL: cls(
                priority=NotificationPriority.CRITICAL,
                response_time=timedelta(minutes=15),
                emoji="🚨",
                requires_acknowledgment=True
            ),
            NotificationPriority.HIGH: cls(
                priority=NotificationPriority.HIGH,
                response_time=timedelta(minutes=30),
                emoji="⚠️",
                requires_acknowledgment=True
            ),
            NotificationPriority.MEDIUM: cls(
                priority=NotificationPriority.MEDIUM,
                response_time=timedelta(hours=2),
                emoji="🔧",
                requires_acknowledgment=False
            ),
            NotificationPriority.LOW: cls(
                priority=NotificationPriority.LOW,
                response_time=timedelta(hours=4),
                emoji="💡",
                requires_acknowledgment=False
            ),
            NotificationPriority.INFO: cls(
                priority=NotificationPriority.INFO,
                response_time=timedelta(hours=24),
                emoji="ℹ️",
                requires_acknowledgment=False
            )
        }

        return sla_config[priority]

    def get_sla_text(self) -> str:
        """Retorna texto formatado do SLA."""
        hours = self.response_time.total_seconds() / 3600

        if hours < 1:
            minutes = int(self.response_time.total_seconds() / 60)
            time_text = f"{minutes} minutos"
        elif hours < 24:
            time_text = f"{int(hours)} hora(s)"
        else:
            days = int(hours / 24)
            time_text = f"{days} dia(s)"

        return f"Resposta em até {time_text}"


@dataclass(frozen=True)
class NotificationFormat:
    """
    Define formato de exibição da notificação.

    Attributes:
        title: Título da notificação
        priority_sla: SLA da notificação
        use_html: Se usa formatação HTML
        disable_preview: Se desabilita preview de links
        use_compact_format: Se usa formato compacto
    """

    title: str
    priority_sla: NotificationSLA
    use_html: bool = True
    disable_preview: bool = True
    use_compact_format: bool = False

    def get_formatted_title(self) -> str:
        """Retorna título formatado com emoji e prioridade."""
        emoji = self.priority_sla.emoji
        priority_name = self.priority_sla.priority.value.upper()

        if self.priority_sla.priority == NotificationPriority.CRITICAL:
            return f"{emoji} <b>{self.title.upper()}</b> {emoji}"

        return f"{emoji} <b>{self.title.upper()}</b>"


def determine_notification_priority(
    urgency_level: Optional[str],
    category: Optional[str],
    has_attachments: bool = False
) -> NotificationPriority:
    """
    Determina prioridade da notificação baseado em critérios.

    Args:
        urgency_level: Nível de urgência reportado
        category: Categoria do problema
        has_attachments: Se tem anexos (screenshots, etc.)

    Returns:
        NotificationPriority: Prioridade determinada
    """
    # Urgência explícita tem prioridade
    if urgency_level == "high":
        return NotificationPriority.CRITICAL

    if urgency_level == "medium":
        return NotificationPriority.HIGH

    # Categorias críticas
    critical_categories = ["connectivity", "outage", "service_down"]
    if category in critical_categories:
        return NotificationPriority.HIGH

    # Performance com evidências (screenshots) = prioridade média-alta
    if category == "performance" and has_attachments:
        return NotificationPriority.MEDIUM

    # Configuração e equipamento = prioridade média
    if category in ["configuration", "equipment"]:
        return NotificationPriority.MEDIUM

    # Outros casos = prioridade baixa
    return NotificationPriority.LOW