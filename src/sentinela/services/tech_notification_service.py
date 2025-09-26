import logging
from datetime import datetime, timedelta
from telegram import Bot

from src.sentinela.core.config import TELEGRAM_TOKEN, TECH_NOTIFICATION_CHANNEL_ID

logger = logging.getLogger(__name__)

async def notify_tech_team_new_ticket(ticket_data: dict, user_data: dict, protocol: str):
    """
    Envia notificação para o canal técnico quando um novo chamado é aberto.

    Args:
        ticket_data: Dados do ticket criado
        user_data: Dados do usuário/cliente
        protocol: Protocolo do atendimento
    """
    try:
        # Verifica se o canal técnico está configurado
        if not TECH_NOTIFICATION_CHANNEL_ID:
            logger.warning(f"Canal técnico não configurado - notificação do ticket {protocol} não enviada")
            return

        # Monta mensagem baseada na prioridade
        urgency = ticket_data.get('urgency_level', 'normal')

        if urgency == 'high':
            await send_critical_notification(ticket_data, user_data, protocol)
        elif urgency == 'medium':
            await send_medium_notification(ticket_data, user_data, protocol)
        else:
            await send_normal_notification(ticket_data, user_data, protocol)

        logger.info(f"Notificação técnica enviada para ticket {protocol}")

    except Exception as e:
        logger.error(f"Erro ao enviar notificação técnica para ticket {protocol}: {e}")

async def send_critical_notification(ticket_data: dict, user_data: dict, protocol: str):
    """Envia notificação para chamados críticos (alta prioridade)"""
    try:
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category_name = get_category_display_name(ticket_data.get('category'))

        # Calcula tempo como cliente
        time_as_client = calculate_client_time(user_data.get('created_at'))

        # Informações enriquecidas da integração HubSoft
        hubsoft_id = ticket_data.get('hubsoft_atendimento_id')
        origem_sistema = "🤖 Bot Telegram (HubSoft Integrado)" if hubsoft_id else "🤖 Bot Telegram (Local)"
        protocolo_display = f"#{protocol}" if protocol.isdigit() else protocol

        # Status da integração
        integracao_status = ""
        if hubsoft_id:
            integracao_status = f"✅ <b>Sincronizado com HubSoft</b> (ID: {hubsoft_id})\n"
        else:
            integracao_status = f"⚠️ <b>Aguardando sincronização HubSoft</b>\n"

        message = (
            f"🚨⚡️ <b>CHAMADO CRÍTICO - {category_name.upper()}</b>\n\n"
            f"📋 <b>Protocolo:</b> {protocolo_display}\n"
            f"🔗 <b>Sistema:</b> {origem_sistema}\n"
            f"{integracao_status}"
            f"🕒 <b>Horário:</b> {current_time}\n\n"
            f"👤 <b>CLIENTE:</b>\n"
            f"• Nome: <b>{client_name}</b>\n"
            f"• CPF: {mask_cpf(user_data.get('cpf', ''))}\n"
            f"• Contrato: {user_data.get('service_name', 'Plano OnCabo')}\n"
            f"• Cliente desde: {time_as_client}\n"
            f"• User ID: #{ticket_data.get('user_id', 'N/A')}\n\n"
            f"🎮 <b>PROBLEMA RELATADO:</b>\n"
            f"• Categoria: <b>{category_name}</b>\n"
            f"• Jogo afetado: <b>{affected_game}</b>\n"
            f"• Iniciado: {get_timing_display_name(ticket_data.get('problem_started'))}\n"
            f"• Prioridade: 🚨 <b>ALTA</b>\n"
            f"• Origem: Via formulário conversacional\n\n"
            f"📝 <b>Descrição completa:</b>\n"
            f"<i>\"{truncate_text(ticket_data.get('description', ''), 200)}\"</i>\n\n"
            f"🔧 <b>AÇÕES RECOMENDADAS:</b>\n"
            f"{get_recommended_actions(ticket_data.get('category'), affected_game)}\n\n"
            f"🎯 <b>CONTEXTO TÉCNICO:</b>\n"
            f"• Coletado via bot inteligente\n"
            f"• Dados validados automaticamente\n"
            f"• Cliente guiado no diagnóstico\n"
            f"• Categorização automática de prioridade\n"
            f"{get_attachments_info(ticket_data)}\n\n"
            f"───────────────────────────────────\n"
            f"📞 Responder no tópico 🆘 Suporte Gamer mencionando {protocolo_display}"
        )

        await send_to_tech_channel(message)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação crítica: {e}")

async def send_medium_notification(ticket_data: dict, user_data: dict, protocol: str):
    """Envia notificação para chamados de média prioridade"""
    try:
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category_name = get_category_display_name(ticket_data.get('category'))

        # Informações da integração
        hubsoft_id = ticket_data.get('hubsoft_atendimento_id')
        protocolo_display = f"#{protocol}" if protocol.isdigit() else protocol
        sync_status = "🔄 HubSoft" if hubsoft_id else "📱 Local"

        message = (
            f"🔧 <b>NOVO CHAMADO - {category_name.upper()}</b>\n\n"
            f"📋 <b>Protocolo:</b> {protocolo_display} | {sync_status}\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"🎮 <b>Problema:</b> {affected_game} - {category_name}\n"
            f"🕒 <b>Horário:</b> {current_time}\n"
            f"⚡️ <b>Prioridade:</b> MÉDIA\n"
            f"🤖 <b>Origem:</b> Bot conversacional\n"
            f"{get_attachments_info(ticket_data, compact=True)}\n\n"
            f"📝 <b>Resumo:</b> <i>{truncate_text(ticket_data.get('description', ''), 150)}</i>\n\n"
            f"🔗 Responder no tópico 🆘 Suporte Gamer com {protocolo_display}"
        )

        await send_to_tech_channel(message)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação média: {e}")

async def send_normal_notification(ticket_data: dict, user_data: dict, protocol: str):
    """Envia notificação para chamados normais"""
    try:
        current_time = datetime.now().strftime("%H:%M")
        client_name = user_data.get('client_name', 'Cliente')
        affected_game = ticket_data.get('affected_game', 'Não especificado')
        category_name = get_category_display_name(ticket_data.get('category'))

        # Status de sincronização simplificado para notificação normal
        hubsoft_id = ticket_data.get('hubsoft_atendimento_id')
        protocolo_display = f"#{protocol}" if protocol.isdigit() else protocol
        integration_emoji = "🔄" if hubsoft_id else "📱"

        # Info compacta sobre anexos
        attachments_compact = get_attachments_info(ticket_data, compact=True, emoji_only=True)

        message = (
            f"💡 <b>SUPORTE TÉCNICO - {category_name.upper()}</b>\n\n"
            f"📋 {protocolo_display} {integration_emoji} | {client_name} | {affected_game} {attachments_compact}\n"
            f"🕒 {current_time} | Prioridade: Normal | 🤖 Bot\n\n"
            f"📝 <i>{truncate_text(ticket_data.get('description', ''), 100)}</i>\n\n"
            f"📞 Responder no 🆘 Suporte Gamer"
        )

        await send_to_tech_channel(message)

    except Exception as e:
        logger.error(f"Erro ao enviar notificação normal: {e}")

async def send_to_tech_channel(message: str):
    """Envia mensagem para o canal técnico"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=TECH_NOTIFICATION_CHANNEL_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para canal técnico: {e}")
        raise

def get_category_display_name(category: str) -> str:
    """Converte categoria interna para nome exibido"""
    category_map = {
        'connectivity': 'Conectividade/Ping',
        'performance': 'Performance Gaming',
        'configuration': 'Configuração',
        'equipment': 'Equipamento',
        'other': 'Outro'
    }
    return category_map.get(category, category or 'Não especificado')

def get_timing_display_name(timing: str) -> str:
    """Converte timing interno para nome exibido"""
    timing_map = {
        'now': 'Agora mesmo',
        'yesterday': 'Ontem',
        'this_week': 'Esta semana',
        'last_week': 'Semana passada',
        'long_time': 'Há mais tempo',
        'always': 'Sempre foi assim'
    }
    return timing_map.get(timing, timing or 'Não especificado')

def get_recommended_actions(category: str, game: str) -> str:
    """Retorna ações recomendadas baseadas na categoria e jogo"""
    actions = {
        'connectivity': [
            "• Verificar status da região/provedor",
            f"• Análise de rota até servidores {game}",
            "• Teste de QoS no plano do cliente",
            "• Verificar congestionamento de rede"
        ],
        'performance': [
            "• Análise de configurações de rede",
            "• Verificar limitações do plano atual",
            f"• Orientações específicas para {game}",
            "• Teste de velocidade e latência"
        ],
        'configuration': [
            "• Orientação técnica personalizada",
            f"• Configurações otimizadas para {game}",
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

    category_actions = actions.get(category, ["• Análise técnica personalizada"])
    return "\n".join(category_actions)

def calculate_client_time(created_at: str) -> str:
    """Calcula tempo como cliente de forma amigável"""
    if not created_at:
        return "Cliente OnCabo"

    try:
        # Tenta parsear diferentes formatos de data
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")

        days_diff = (datetime.now() - created_date).days

        if days_diff < 7:
            return f"Cliente há {days_diff} dias"
        elif days_diff < 30:
            return f"Cliente há {days_diff//7} semanas"
        elif days_diff < 365:
            months = days_diff // 30
            return f"Cliente há {months} {'mês' if months == 1 else 'meses'}"
        else:
            years = days_diff // 365
            return f"Cliente há {years} {'ano' if years == 1 else 'anos'}"

    except Exception as e:
        logger.error(f"Erro ao calcular tempo como cliente: {e}")
        return "Cliente OnCabo"

def mask_cpf(cpf: str) -> str:
    """Mascara CPF para exibição (segurança)"""
    if not cpf or len(cpf) < 11:
        return "***.***.***-**"

    # Remove formatação se existir
    clean_cpf = ''.join(filter(str.isdigit, cpf))

    if len(clean_cpf) == 11:
        return f"{clean_cpf[:3]}.{clean_cpf[3:6]}.***-{clean_cpf[9:]}"

    return "***.***.***-**"

def truncate_text(text: str, max_length: int) -> str:
    """Trunca texto preservando palavras"""
    if not text or len(text) <= max_length:
        return text or ""

    truncated = text[:max_length]

    # Encontra o último espaço para não cortar palavra
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Se o último espaço não está muito longe
        truncated = truncated[:last_space]

    return truncated + "..."

async def notify_ticket_update(protocol: str, status: str, update_message: str = None):
    """
    Notifica sobre atualizações em tickets existentes.
    Para uso futuro quando integrar com HubSoft.
    """
    try:
        current_time = datetime.now().strftime("%H:%M")

        status_emoji = {
            'in_progress': '🔄',
            'resolved': '✅',
            'closed': '🔒',
            'escalated': '⬆️'
        }

        emoji = status_emoji.get(status, '📝')

        message = (
            f"{emoji} <b>ATUALIZAÇÃO DE CHAMADO</b>\n\n"
            f"📋 <b>Protocolo:</b> {protocol}\n"
            f"🔄 <b>Status:</b> {status.title()}\n"
            f"🕒 <b>Horário:</b> {current_time}\n"
        )

        if update_message:
            message += f"\n💬 <b>Detalhes:</b> {update_message}"

        await send_to_tech_channel(message)

        logger.info(f"Notificação de update enviada para ticket {protocol}")

    except Exception as e:
        logger.error(f"Erro ao enviar notificação de update: {e}")

async def send_daily_summary():
    """
    Envia resumo diário de chamados.
    Para uso futuro com cron job.
    """
    try:
        # TODO: Implementar quando tiver estatísticas mais robustas
        pass
    except Exception as e:
        logger.error(f"Erro ao enviar resumo diário: {e}")

def get_attachments_info(ticket_data: dict, compact: bool = False, emoji_only: bool = False) -> str:
    """
    Retorna informações sobre anexos formatadas para notificações

    Args:
        ticket_data: Dados do ticket
        compact: Se True, formato compacto
        emoji_only: Se True, apenas emoji (para linha única)

    Returns:
        String formatada com info dos anexos
    """
    try:
        attachments = ticket_data.get('attachments', [])

        if not attachments:
            if emoji_only:
                return ""
            return "• Anexos: Nenhum" if compact else "• Sem anexos enviados"

        count = len(attachments)

        if emoji_only:
            return f"📎{count}"

        if compact:
            return f"📎 {count} anexo(s)"

        # Formato completo
        return f"• Anexos: {count} imagem(ns) anexada(s) ✅"

    except Exception as e:
        logger.warning(f"Erro ao processar info de anexos: {e}")
        return "" if emoji_only else "• Anexos: Erro ao processar"