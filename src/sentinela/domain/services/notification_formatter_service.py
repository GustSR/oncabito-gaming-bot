"""
Notification Formatter Service.

Serviço de domínio responsável por formatar notificações
técnicas de acordo com o contexto e prioridade.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..value_objects.notification_priority import (
    NotificationPriority,
    NotificationSLA,
    NotificationFormat
)

logger = logging.getLogger(__name__)


class NotificationFormatterService:
    """
    Serviço de domínio para formatação de notificações.

    Implementa lógica de formatação de mensagens baseada
    em prioridade, contexto e destinatário.
    """

    # Mapeamentos de categorias
    CATEGORY_NAMES = {
        'connectivity': 'Conectividade/Ping',
        'performance': 'Performance Gaming',
        'configuration': 'Configuração',
        'equipment': 'Equipamento',
        'outage': 'Indisponibilidade',
        'service_down': 'Serviço Fora do Ar',
        'other': 'Outro'
    }

    # Mapeamentos de timing
    TIMING_NAMES = {
        'now': 'Agora mesmo',
        'yesterday': 'Ontem',
        'this_week': 'Esta semana',
        'last_week': 'Semana passada',
        'long_time': 'Há mais tempo',
        'always': 'Sempre foi assim'
    }

    # Ações recomendadas por categoria
    RECOMMENDED_ACTIONS = {
        'connectivity': [
            "• Verificar status da região/provedor",
            "• Análise de rota até servidores do jogo",
            "• Teste de QoS no plano do cliente",
            "• Verificar congestionamento de rede"
        ],
        'performance': [
            "• Análise de configurações de rede",
            "• Verificar limitações do plano atual",
            "• Orientações específicas para o jogo",
            "• Teste de velocidade e latência"
        ],
        'configuration': [
            "• Orientação técnica personalizada",
            "• Configurações otimizadas para o jogo",
            "• Setup de QoS/priorização",
            "• DNS gaming recomendado"
        ],
        'equipment': [
            "• Diagnóstico remoto do equipamento",
            "• Verificar necessidade de visita técnica",
            "• Análise de interferências",
            "• Possível troca/upgrade"
        ]
    }

    def format_critical_notification(
        self,
        ticket_data: Dict[str, Any],
        user_data: Dict[str, Any],
        protocol: str
    ) -> str:
        """
        Formata notificação crítica com todas as informações detalhadas.

        Args:
            ticket_data: Dados do ticket
            user_data: Dados do usuário/cliente
            protocol: Protocolo do atendimento

        Returns:
            str: Mensagem formatada em HTML
        """
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category = ticket_data.get('category', 'other')
        category_name = self.get_category_name(category)

        # Informações de integração HubSoft
        hubsoft_protocol = ticket_data.get('hubsoft_protocol')
        protocolo_display = hubsoft_protocol or f"ATD{protocol.zfill(6)}"
        origem_sistema = "🔄 HubSoft Integrado" if hubsoft_protocol else "📱 Sistema Local"

        # Status de integração
        integracao_status = (
            "✅ <b>Sincronizado HubSoft</b>\n" if hubsoft_protocol
            else "⚠️ <b>Pendente sincronização</b>\n"
        )

        # Tempo como cliente
        time_as_client = self._calculate_client_time(user_data)

        # SLA
        sla = NotificationSLA.for_priority(NotificationPriority.CRITICAL)

        message = (
            f"🚨 <b>NOVO CHAMADO CRÍTICO</b> 🚨\n\n"
            f"📋 <b>Protocolo:</b> <code>{protocolo_display}</code>\n"
            f"🔗 <b>Status:</b> {origem_sistema}\n"
            f"{integracao_status}"
            f"🕒 <b>Abertura:</b> {current_time}\n\n"
            f"👤 <b>DADOS DO CLIENTE</b>\n"
            f"• <b>Nome:</b> {client_name}\n"
            f"• <b>CPF:</b> <code>{self._mask_cpf(user_data.get('cpf', ''))}</code>\n"
            f"• <b>Plano:</b> {user_data.get('service_name', 'OnCabo Gaming')}\n"
            f"• <b>Histórico:</b> {time_as_client}\n"
            f"• <b>TG ID:</b> <code>{ticket_data.get('user_id', 'N/A')}</code>\n\n"
            f"⚡ <b>DETALHES DO PROBLEMA</b>\n"
            f"• <b>Categoria:</b> {category_name}\n"
            f"• <b>Jogo/Serviço:</b> {affected_game}\n"
            f"• <b>Quando começou:</b> {self.get_timing_name(ticket_data.get('problem_started'))}\n"
            f"• <b>Urgência:</b> 🚨 ALTA PRIORIDADE\n"
            f"{self._format_attachments_info(ticket_data, admin_format=True)}\n\n"
            f"📝 <b>RELATO DO CLIENTE:</b>\n"
            f"<blockquote>{self._truncate_text(ticket_data.get('description', ''), 180)}</blockquote>\n\n"
            f"🔧 <b>SUGESTÕES TÉCNICAS:</b>\n"
            f"{self._get_recommended_actions(category, affected_game)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>AÇÃO NECESSÁRIA:</b> Atender no 🆘 Suporte Gamer usando <code>{protocolo_display}</code>\n"
            f"⏰ <b>SLA:</b> {sla.get_sla_text()} para chamados críticos"
        )

        return message

    def format_high_notification(
        self,
        ticket_data: Dict[str, Any],
        user_data: Dict[str, Any],
        protocol: str
    ) -> str:
        """
        Formata notificação de alta prioridade (formato médio).

        Args:
            ticket_data: Dados do ticket
            user_data: Dados do usuário/cliente
            protocol: Protocolo do atendimento

        Returns:
            str: Mensagem formatada em HTML
        """
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category_name = self.get_category_name(ticket_data.get('category'))

        # Protocolo
        hubsoft_protocol = ticket_data.get('hubsoft_protocol')
        protocolo_display = hubsoft_protocol or f"ATD{protocol.zfill(6)}"
        sync_status = "🔄 HubSoft" if hubsoft_protocol else "📱 Local"

        message = (
            f"🔧 <b>NOVO CHAMADO - {category_name.upper()}</b>\n\n"
            f"📋 <b>Protocolo:</b> {protocolo_display} | {sync_status}\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"🎮 <b>Problema:</b> {affected_game} - {category_name}\n"
            f"🕒 <b>Horário:</b> {current_time}\n"
            f"⚡️ <b>Prioridade:</b> ALTA\n"
            f"🤖 <b>Origem:</b> Bot conversacional\n"
            f"{self._format_attachments_info(ticket_data, compact=True)}\n\n"
            f"📝 <b>Resumo:</b> <i>{self._truncate_text(ticket_data.get('description', ''), 150)}</i>\n\n"
            f"🔗 Responder no tópico 🆘 Suporte Gamer com {protocolo_display}"
        )

        return message

    def format_normal_notification(
        self,
        ticket_data: Dict[str, Any],
        user_data: Dict[str, Any],
        protocol: str
    ) -> str:
        """
        Formata notificação normal (formato compacto).

        Args:
            ticket_data: Dados do ticket
            user_data: Dados do usuário/cliente
            protocol: Protocolo do atendimento

        Returns:
            str: Mensagem formatada em HTML
        """
        current_time = datetime.now().strftime("%H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category_name = self.get_category_name(ticket_data.get('category'))

        # Protocolo
        hubsoft_protocol = ticket_data.get('hubsoft_protocol')
        protocolo_display = hubsoft_protocol or f"ATD{protocol.zfill(6)}"
        integration_emoji = "🔄" if hubsoft_protocol else "📱"

        # Info compacta sobre anexos
        attachments_compact = self._format_attachments_info(ticket_data, emoji_only=True)

        message = (
            f"💡 <b>SUPORTE TÉCNICO - {category_name.upper()}</b>\n\n"
            f"📋 {protocolo_display} {integration_emoji} | {client_name} | {affected_game} {attachments_compact}\n"
            f"🕒 {current_time} | Prioridade: Normal | 🤖 Bot\n\n"
            f"📝 <i>{self._truncate_text(ticket_data.get('description', ''), 100)}</i>\n\n"
            f"📞 Responder no 🆘 Suporte Gamer"
        )

        return message

    def format_update_notification(
        self,
        protocol: str,
        status: str,
        update_message: Optional[str] = None
    ) -> str:
        """
        Formata notificação de atualização de ticket.

        Args:
            protocol: Protocolo do ticket
            status: Novo status
            update_message: Mensagem de atualização (opcional)

        Returns:
            str: Mensagem formatada
        """
        current_time = datetime.now().strftime("%H:%M")

        status_emoji = {
            'in_progress': '🔄',
            'resolved': '✅',
            'closed': '🔒',
            'escalated': '⬆️',
            'on_hold': '⏸',
            'pending_client': '⏳'
        }

        status_names = {
            'in_progress': 'Em Andamento',
            'resolved': 'Resolvido',
            'closed': 'Fechado',
            'escalated': 'Escalado',
            'on_hold': 'Em Espera',
            'pending_client': 'Aguardando Cliente'
        }

        emoji = status_emoji.get(status, '📝')
        status_name = status_names.get(status, status.title())

        message = (
            f"{emoji} <b>ATUALIZAÇÃO DE CHAMADO</b>\n\n"
            f"📋 <b>Protocolo:</b> {protocol}\n"
            f"🔄 <b>Status:</b> {status_name}\n"
            f"🕒 <b>Horário:</b> {current_time}\n"
        )

        if update_message:
            message += f"\n💬 <b>Detalhes:</b> {update_message}"

        return message

    def get_category_name(self, category: Optional[str]) -> str:
        """Retorna nome formatado da categoria."""
        return self.CATEGORY_NAMES.get(category, category or 'Não especificado')

    def get_timing_name(self, timing: Optional[str]) -> str:
        """Retorna nome formatado do timing."""
        return self.TIMING_NAMES.get(timing, timing or 'Não especificado')

    def _get_recommended_actions(self, category: str, game: str) -> str:
        """Retorna ações recomendadas formatadas."""
        actions = self.RECOMMENDED_ACTIONS.get(
            category,
            ["• Análise técnica personalizada"]
        )

        # Personaliza com nome do jogo
        personalized_actions = [
            action.replace("do jogo", f"de {game}") if game != "Não especificado" else action
            for action in actions
        ]

        return "\n".join(personalized_actions)

    def _calculate_client_time(self, user_data: Dict[str, Any]) -> str:
        """Calcula e formata tempo como cliente."""
        date_field = user_data.get('data_habilitacao') or user_data.get('created_at')

        if not date_field:
            return "Cliente OnCabo"

        try:
            reference_date = None

            # Formato brasileiro dd/mm/yyyy
            if '/' in str(date_field):
                try:
                    reference_date = datetime.strptime(str(date_field), "%d/%m/%Y")
                except:
                    pass

            # Formato ISO
            if not reference_date:
                try:
                    reference_date = datetime.fromisoformat(str(date_field).replace('Z', '+00:00'))
                except:
                    try:
                        reference_date = datetime.strptime(str(date_field), "%Y-%m-%d %H:%M:%S")
                    except:
                        pass

            if not reference_date:
                return "Cliente OnCabo"

            days_diff = (datetime.now() - reference_date).days

            if days_diff < 0:
                return "Cliente OnCabo"
            elif days_diff < 7:
                return f"Cliente há {days_diff} dias"
            elif days_diff < 30:
                weeks = max(1, days_diff // 7)
                return f"Cliente há {weeks} {'semana' if weeks == 1 else 'semanas'}"
            elif days_diff < 365:
                months = max(1, days_diff // 30)
                return f"Cliente há {months} {'mês' if months == 1 else 'meses'}"
            else:
                years = max(1, days_diff // 365)
                return f"Cliente há {years} {'ano' if years == 1 else 'anos'}"

        except Exception as e:
            logger.error(f"Erro ao calcular tempo como cliente: {e}")
            return "Cliente OnCabo"

    def _mask_cpf(self, cpf: str) -> str:
        """Mascara CPF para exibição segura."""
        if not cpf or len(cpf) < 11:
            return "***.***.***-**"

        clean_cpf = ''.join(filter(str.isdigit, cpf))

        if len(clean_cpf) == 11:
            return f"{clean_cpf[:3]}.{clean_cpf[3:6]}.***-{clean_cpf[9:]}"

        return "***.***.***-**"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto preservando palavras."""
        if not text or len(text) <= max_length:
            return text or ""

        truncated = text[:max_length]

        # Encontra o último espaço
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]

        return truncated + "..."

    def _format_attachments_info(
        self,
        ticket_data: Dict[str, Any],
        compact: bool = False,
        emoji_only: bool = False,
        admin_format: bool = False
    ) -> str:
        """Formata informações sobre anexos."""
        attachments = ticket_data.get('attachments', [])

        if not attachments:
            if emoji_only:
                return ""
            if admin_format:
                return "• <b>Anexos:</b> Nenhum"
            return "• Anexos: Nenhum" if compact else "• Sem anexos enviados"

        count = len(attachments)

        if emoji_only:
            return f"📎{count}"

        if admin_format:
            return f"• <b>Anexos:</b> 📎 {count} arquivo(s) {'📷 imagem' if count == 1 else '📷 imagens'}"

        if compact:
            return f"📎 {count} anexo(s)"

        return f"• Anexos: {count} imagem(ns) anexada(s) ✅"