import logging
import json
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID
from src.sentinela.clients.db_client import (
    can_create_support_ticket, start_support_conversation, get_support_conversation,
    update_support_conversation, save_support_ticket, get_user_data, get_active_support_tickets
)

logger = logging.getLogger(__name__)

class SupportFormManager:
    """Gerencia o formulário conversacional de suporte"""

    # Configuração dos passos do formulário
    STEPS = {
        1: "category_selection",
        2: "game_selection",
        3: "timing_selection",
        4: "description_input",
        5: "confirmation"
    }

    # Categorias de problemas
    CATEGORIES = {
        "connectivity": "🌐 Conectividade/Ping",
        "performance": "🎮 Performance em Jogos",
        "configuration": "⚙️ Configuração/Otimização",
        "equipment": "🔧 Problema com Equipamento",
        "other": "📞 Outro"
    }

    # Jogos populares
    POPULAR_GAMES = {
        "valorant": "⚡️ Valorant",
        "cs2": "🎯 CS2",
        "lol": "🏆 League of Legends",
        "fortnite": "🌍 Fortnite",
        "apex": "🎮 Apex Legends",
        "overwatch": "🦸 Overwatch 2",
        "mobile_legends": "📱 Mobile Legends",
        "dota2": "⚔️ Dota 2",
        "all_games": "🌐 Todos os jogos",
        "other_game": "📝 Outro jogo"
    }

    # Opções de tempo
    TIMING_OPTIONS = {
        "now": "🚨 Agora mesmo / Hoje",
        "yesterday": "📅 Ontem",
        "this_week": "📆 Esta semana",
        "last_week": "🗓️ Semana passada",
        "long_time": "⏳ Há mais tempo",
        "always": "🔄 Sempre foi assim"
    }

async def handle_support_request(user_id: int, username: str, user_mention: str):
    """
    Inicia processo de suporte para o usuário.

    Args:
        user_id: ID do usuário no Telegram
        username: Nome de usuário
        user_mention: Mention formatado do usuário
    """
    try:
        # Verifica se pode criar ticket (anti-spam)
        permission = can_create_support_ticket(user_id)

        if not permission['can_create']:
            await send_support_blocked_message(user_id, permission)
            return

        # Busca dados do cliente no banco
        user_data = get_user_data(user_id)
        if not user_data:
            await send_client_not_found_message(user_id)
            return

        # Inicia conversa de formulário
        if start_support_conversation(user_id, username):
            await send_welcome_support_message(user_id, user_data, user_mention)
        else:
            await send_error_message(user_id, "Erro ao iniciar formulário de suporte")

    except Exception as e:
        logger.error(f"Erro ao processar solicitação de suporte para {username}: {e}")
        await send_error_message(user_id, "Erro interno no sistema de suporte")

async def handle_support_message(user_id: int, message_text: str, username: str):
    """
    Processa mensagem durante o formulário de suporte.

    Args:
        user_id: ID do usuário
        message_text: Texto da mensagem
        username: Nome de usuário
    """
    try:
        # Busca conversa ativa
        conversation = get_support_conversation(user_id)
        if not conversation:
            return False  # Não é conversa de suporte

        current_step = conversation['current_step']
        form_data = json.loads(conversation['form_data'] or '{}')

        # Processa baseado no passo atual
        if current_step == 4:  # Descrição detalhada
            await process_description_step(user_id, message_text, form_data, username)
        elif message_text.startswith('/') or message_text in ['📝 Outro jogo', '📞 Outro']:
            await process_other_input(user_id, message_text, current_step, form_data)

        return True  # Mensagem processada

    except Exception as e:
        logger.error(f"Erro ao processar mensagem de suporte de {username}: {e}")
        return False

async def handle_support_callback(user_id: int, callback_data: str, username: str):
    """
    Processa cliques em botões do formulário de suporte.

    Args:
        user_id: ID do usuário
        callback_data: Dados do callback
        username: Nome de usuário
    """
    try:
        conversation = get_support_conversation(user_id)
        if not conversation:
            return False

        current_step = conversation['current_step']
        form_data = json.loads(conversation['form_data'] or '{}')

        # Remove prefixo 'support_'
        action = callback_data.replace('support_', '') if callback_data.startswith('support_') else callback_data

        if current_step == 1:  # Categoria
            await process_category_selection(user_id, action, form_data, username)
        elif current_step == 2:  # Jogo
            await process_game_selection(user_id, action, form_data, username)
        elif current_step == 3:  # Timing
            await process_timing_selection(user_id, action, form_data, username)
        elif current_step == 5:  # Confirmação
            await process_confirmation(user_id, action, form_data, username)

        return True

    except Exception as e:
        logger.error(f"Erro ao processar callback de suporte de {username}: {e}")
        return False

async def send_welcome_support_message(user_id: int, user_data: dict, user_mention: str):
    """Envia mensagem de boas-vindas do formulário de suporte"""
    try:
        client_name = user_data.get('client_name', 'Cliente')
        service_name = user_data.get('service_name', 'Plano OnCabo')

        # Calcula tempo como cliente (aproximado)
        created_at = user_data.get('created_at', '')
        time_as_client = "Cliente OnCabo"
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_diff = (datetime.now() - created_date).days
                if days_diff < 30:
                    time_as_client = f"Cliente há {days_diff} dias"
                elif days_diff < 365:
                    time_as_client = f"Cliente há {days_diff//30} meses"
                else:
                    time_as_client = f"Cliente há {days_diff//365} anos"
            except:
                pass

        welcome_text = (
            f"🎮 <b>Olá, {client_name}!</b>\n\n"
            f"Sou o assistente virtual da OnCabo e estou aqui para te ajudar com qualquer problema de gaming! 💪\n\n"
            f"🔍 Vejo que você é <b>{time_as_client}</b> e tem o <b>{service_name}</b> - perfeito para gaming!\n\n"
            f"Vamos resolver seu problema juntos? Preciso de algumas informações para criar seu atendimento oficial no nosso sistema.\n\n"
            f"⏱️ Levará apenas <b>2-3 minutos</b> e você terá um protocolo para acompanhar.\n\n"
            f"🚀 <b>Vamos começar?</b>"
        )

        # Cria botões para categorias
        keyboard = create_category_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=welcome_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

            # Envia progress bar
            progress_text = "🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓░░░░] 1/5\n\n✅ Iniciado\n🔄 Tipo do problema...\n⏳ Jogo afetado...\n⏳ Detalhes...\n⏳ Confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de boas-vindas de suporte: {e}")

def create_category_keyboard():
    """Cria teclado inline para seleção de categoria"""
    keyboard = []
    for key, value in SupportFormManager.CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"support_{key}")])

    return InlineKeyboardMarkup(keyboard)

def create_game_keyboard():
    """Cria teclado inline para seleção de jogo"""
    keyboard = []
    games = list(SupportFormManager.POPULAR_GAMES.items())

    # Organiza em pares para layout mais compacto
    for i in range(0, len(games), 2):
        row = []
        row.append(InlineKeyboardButton(games[i][1], callback_data=f"support_{games[i][0]}"))
        if i + 1 < len(games):
            row.append(InlineKeyboardButton(games[i+1][1], callback_data=f"support_{games[i+1][0]}"))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def create_timing_keyboard():
    """Cria teclado inline para seleção de timing"""
    keyboard = []
    for key, value in SupportFormManager.TIMING_OPTIONS.items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"support_{key}")])

    return InlineKeyboardMarkup(keyboard)

def create_confirmation_keyboard():
    """Cria teclado inline para confirmação final"""
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRMAR E CRIAR ATENDIMENTO", callback_data="support_confirm")],
        [InlineKeyboardButton("📝 REVISAR INFORMAÇÕES", callback_data="support_review")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="support_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def process_category_selection(user_id: int, category: str, form_data: dict, username: str):
    """Processa seleção de categoria"""
    try:
        form_data['category'] = category
        form_data['category_name'] = SupportFormManager.CATEGORIES.get(category, category)

        # Atualiza conversa para próximo passo
        update_support_conversation(user_id, 2, 'game_selection', json.dumps(form_data))

        # Envia pergunta sobre jogo
        game_text = (
            f"🎮 <b>Entendi! E me conta, qual jogo está sendo mais afetado?</b>\n\n"
            f"🔥 <b>POPULARES:</b>"
        )

        keyboard = create_game_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=game_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

            # Atualiza progress
            progress_text = "🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓░░░] 2/5\n\n✅ Tipo do problema: " + form_data['category_name'] + "\n🔄 Jogo afetado...\n⏳ Quando começou...\n⏳ Detalhes...\n⏳ Confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao processar seleção de categoria para {username}: {e}")

async def process_game_selection(user_id: int, game: str, form_data: dict, username: str):
    """Processa seleção de jogo"""
    try:
        form_data['game'] = game
        form_data['game_name'] = SupportFormManager.POPULAR_GAMES.get(game, game)

        # Atualiza conversa para próximo passo
        update_support_conversation(user_id, 3, 'timing_selection', json.dumps(form_data))

        # Envia pergunta sobre timing
        timing_text = (
            f"⏰ <b>Para entender melhor a situação, quando você começou a notar esse problema?</b>\n\n"
            f"💭 Isso me ajuda a identificar se é algo pontual ou estrutural!"
        )

        keyboard = create_timing_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=timing_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

            # Atualiza progress
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓░░] 3/5\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n🔄 Quando começou...\n⏳ Detalhes...\n⏳ Confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao processar seleção de jogo para {username}: {e}")

async def process_timing_selection(user_id: int, timing: str, form_data: dict, username: str):
    """Processa seleção de timing"""
    try:
        form_data['timing'] = timing
        form_data['timing_name'] = SupportFormManager.TIMING_OPTIONS.get(timing, timing)

        # Atualiza conversa para próximo passo
        update_support_conversation(user_id, 4, 'description_input', json.dumps(form_data))

        # Envia solicitação de descrição
        description_text = (
            f"📝 <b>Agora, me descreva o problema com suas palavras!</b>\n\n"
            f"Pode incluir:\n"
            f"• 🎯 O que exatamente acontece\n"
            f"• 🕐 Em que horários é pior\n"
            f"• 📊 Valores que você vê (ping, FPS, etc)\n"
            f"• 🔧 O que já tentou fazer\n\n"
            f"⌨️ <b>Digite abaixo (máximo 500 caracteres):</b>\n\n"
            f"💡 Quanto mais detalhes, melhor será nossa solução!"
        )

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=description_text,
                parse_mode='HTML'
            )

            # Atualiza progress
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓▓░] 4/5\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n✅ Quando começou: {form_data['timing_name']}\n🔄 Coletando detalhes...\n⏳ Confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao processar seleção de timing para {username}: {e}")

async def process_description_step(user_id: int, description: str, form_data: dict, username: str):
    """Processa descrição detalhada"""
    try:
        # Validação da descrição
        if len(description.strip()) < 10:
            await send_description_too_short(user_id)
            return

        if len(description) > 500:
            description = description[:500] + "..."

        # Sanitiza descrição
        clean_description = sanitize_description(description)
        form_data['description'] = clean_description

        # Atualiza conversa para confirmação
        update_support_conversation(user_id, 5, 'confirmation', json.dumps(form_data))

        # Mostra resumo para confirmação
        await send_confirmation_summary(user_id, form_data, username)

    except Exception as e:
        logger.error(f"Erro ao processar descrição para {username}: {e}")

async def send_confirmation_summary(user_id: int, form_data: dict, username: str):
    """Envia resumo para confirmação"""
    try:
        # Busca dados do usuário
        user_data = get_user_data(user_id)
        client_name = user_data.get('client_name', 'Cliente') if user_data else 'Cliente'

        # Trunca descrição para resumo
        description_preview = form_data['description'][:100] + "..." if len(form_data['description']) > 100 else form_data['description']

        summary_text = (
            f"✅ <b>RESUMO DO SEU ATENDIMENTO:</b>\n\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"🎮 <b>Problema:</b> {form_data['category_name']}\n"
            f"🎯 <b>Jogo:</b> {form_data['game_name']}\n"
            f"⏰ <b>Iniciado:</b> {form_data['timing_name']}\n"
            f"📝 <b>Detalhes:</b> \"{description_preview}\"\n\n"
            f"🔥 <b>Vou criar seu atendimento oficial agora!</b>\n\n"
            f"⚡️ Em poucos segundos você terá seu protocolo!"
        )

        keyboard = create_confirmation_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=summary_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

            # Progress final
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓▓▓] 5/5\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n✅ Quando começou: {form_data['timing_name']}\n✅ Detalhes coletados\n🔄 Aguardando confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao enviar resumo de confirmação para {username}: {e}")

async def process_confirmation(user_id: int, action: str, form_data: dict, username: str):
    """Processa confirmação final"""
    try:
        if action == "confirm":
            await create_support_ticket(user_id, form_data, username)
        elif action == "review":
            # Volta para categoria
            update_support_conversation(user_id, 1, 'category_selection', '{}')
            await send_welcome_support_message(user_id, get_user_data(user_id), f"@{username}")
        elif action == "cancel":
            # Cancela formulário
            update_support_conversation(user_id, 0, 'cancelled', json.dumps(form_data))
            await send_cancellation_message(user_id)

    except Exception as e:
        logger.error(f"Erro ao processar confirmação para {username}: {e}")

async def create_support_ticket(user_id: int, form_data: dict, username: str):
    """Cria ticket de suporte final"""
    try:
        from src.sentinela.services.tech_notification_service import notify_tech_team_new_ticket

        # Busca dados do cliente
        user_data = get_user_data(user_id)
        if not user_data:
            await send_error_message(user_id, "Erro: dados do cliente não encontrados")
            return

        # Monta dados do ticket
        ticket_data = {
            'user_id': user_id,
            'username': username,
            'user_mention': f"@{username}",
            'client_id': user_data.get('user_id'),  # Usar user_id como client_id temporário
            'cpf': user_data.get('cpf', ''),
            'client_name': user_data.get('client_name', ''),
            'category': form_data['category'],
            'affected_game': form_data['game'],
            'problem_started': form_data['timing'],
            'description': form_data['description'],
            'urgency_level': calculate_urgency(form_data),
            'topic_thread_id': 148  # ID do tópico de suporte
        }

        # Salva ticket no banco
        ticket_id = save_support_ticket(ticket_data)

        if ticket_id:
            # Por enquanto usa ticket_id local como protocolo
            # Quando integrar com HubSoft, substituir por ID da API
            protocol = f"ATD{ticket_id:06d}"

            # Envia notificação para canal técnico
            await notify_tech_team_new_ticket(ticket_data, user_data, protocol)

            # Envia confirmação para o usuário
            await send_ticket_created_success(user_id, protocol, form_data, user_data)

            # TODO: Aqui será integrado com HubSoft API
            # hubsoft_id = await create_hubsoft_atendimento(ticket_data)
            # update_ticket_hubsoft_id(ticket_id, hubsoft_id)

        else:
            await send_error_message(user_id, "Erro ao criar ticket de suporte")

    except Exception as e:
        logger.error(f"Erro ao criar ticket de suporte para {username}: {e}")
        await send_error_message(user_id, "Erro interno ao criar atendimento")

def calculate_urgency(form_data: dict) -> str:
    """Calcula urgência do ticket baseado nos dados"""
    category = form_data.get('category', '')
    timing = form_data.get('timing', '')

    # Alta urgência para problemas de conectividade que começaram agora
    if category == 'connectivity' and timing in ['now', 'yesterday']:
        return 'high'

    # Média para problemas de performance
    if category == 'performance':
        return 'medium'

    return 'normal'

def sanitize_description(text: str) -> str:
    """Sanitiza descrição do problema"""
    # Remove caracteres especiais desnecessários
    import re

    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)

    # Capitaliza primeira letra
    text = text.strip().capitalize()

    return text

async def send_ticket_created_success(user_id: int, protocol: str, form_data: dict, user_data: dict):
    """Envia mensagem de sucesso na criação do ticket"""
    try:
        client_name = user_data.get('client_name', 'Cliente')
        current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

        success_text = (
            f"🎉 <b>ATENDIMENTO CRIADO COM SUCESSO!</b>\n\n"
            f"📋 <b>Protocolo:</b> #{protocol}\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"🕒 <b>Criado:</b> {current_time}\n"
            f"⚡️ <b>Prioridade:</b> {get_priority_text(calculate_urgency(form_data))}\n\n"
            f"───────────────────────────────────────\n\n"
            f"✅ <b>O QUE ACONTECE AGORA:</b>\n\n"
            f"1️⃣ Nossa equipe técnica foi notificada\n"
            f"2️⃣ Análise inicial em até 30 minutos\n"
            f"3️⃣ Retorno com diagnóstico em até 4 horas\n"
            f"4️⃣ Resolução completa conforme complexidade\n\n"
            f"───────────────────────────────────────\n\n"
            f"📞 <b>ACOMPANHE SEU ATENDIMENTO:</b>\n"
            f"• No tópico 🆘 Suporte Gamer\n"
            f"• Mencione o protocolo #{protocol}\n"
            f"• Ou chame @suporte_oncabo\n\n"
            f"⚡️ <b>RESOLUÇÃO RÁPIDA COMUM EM:</b>\n"
            f"🎮 Ping/Lag: Otimização imediata\n"
            f"⚙️ Configuração: Orientação técnica\n"
            f"🔧 Equipamento: Agendamento se necessário\n\n"
            f"🚀 <b>Relaxa que vamos resolver! A OnCabo cuida dos seus games!</b> 💪"
        )

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=success_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de sucesso: {e}")

def get_priority_text(priority: str) -> str:
    """Converte prioridade para texto amigável"""
    priority_map = {
        'high': 'Alta (problema crítico)',
        'medium': 'Média (problema de performance)',
        'normal': 'Normal (suporte geral)'
    }
    return priority_map.get(priority, 'Normal')

# Mensagens de erro e bloqueio
async def send_support_blocked_message(user_id: int, permission: dict):
    """Envia mensagem quando usuário está bloqueado"""
    try:
        reason = permission['reason']

        if reason == 'active_ticket':
            # Busca tickets ativos
            active_tickets = get_active_support_tickets(user_id)
            ticket_info = f"#{active_tickets[0]['id']:06d}" if active_tickets else "#ATD000000"

            message = (
                f"🎮 <b>Olá!</b> Vejo que você já tem um atendimento em andamento ({ticket_info}).\n\n"
                f"📞 Nossa equipe está trabalhando no seu caso!\n\n"
                f"💡 <b>Para agilizar, você pode:</b>\n"
                f"• Aguardar retorno da equipe técnica\n"
                f"• Adicionar informações ao chamado existente\n"
                f"• Verificar status pelo número do protocolo\n\n"
                f"⏰ <b>Tempo médio de resposta:</b> 2-4 horas úteis"
            )
        elif reason == 'daily_limit':
            message = (
                f"⚠️ <b>Percebo que você já abriu alguns chamados recentemente.</b>\n\n"
                f"🕒 Para garantir qualidade no atendimento, há um limite de 3 chamados por dia.\n\n"
                f"📞 Nossa equipe está analisando seus casos anteriores.\n\n"
                f"🔄 Você poderá abrir um novo chamado amanhã."
            )
        else:
            message = f"⚠️ {permission['message']}\n\nTente novamente mais tarde."

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de bloqueio: {e}")

async def send_client_not_found_message(user_id: int):
    """Envia mensagem quando cliente não é encontrado"""
    message = (
        f"❌ <b>Cliente não encontrado</b>\n\n"
        f"Para usar o suporte, você precisa ser um cliente OnCabo verificado.\n\n"
        f"📝 Use o comando /start para validar seu CPF primeiro."
    )

    bot = Bot(token=TELEGRAM_TOKEN)
    async with bot:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='HTML'
        )

async def send_error_message(user_id: int, error_msg: str):
    """Envia mensagem de erro genérica"""
    message = f"❌ <b>Erro:</b> {error_msg}\n\nTente novamente ou entre em contato com o suporte."

    bot = Bot(token=TELEGRAM_TOKEN)
    async with bot:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='HTML'
        )

async def send_description_too_short(user_id: int):
    """Envia mensagem quando descrição é muito curta"""
    message = (
        f"📝 <b>Descrição muito curta!</b>\n\n"
        f"Para que possamos te ajudar melhor, preciso de pelo menos 10 caracteres descrevendo o problema.\n\n"
        f"💡 <b>Tente incluir:</b>\n"
        f"• O que está acontecendo\n"
        f"• Quando acontece\n"
        f"• Que valores você vê\n\n"
        f"⌨️ <b>Digite uma descrição mais detalhada:</b>"
    )

    bot = Bot(token=TELEGRAM_TOKEN)
    async with bot:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='HTML'
        )

async def send_cancellation_message(user_id: int):
    """Envia mensagem de cancelamento"""
    message = (
        f"❌ <b>Formulário cancelado</b>\n\n"
        f"Sem problemas! Se precisar de ajuda depois, é só usar /suporte novamente.\n\n"
        f"🎮 A OnCabo está sempre aqui para te ajudar!"
    )

    bot = Bot(token=TELEGRAM_TOKEN)
    async with bot:
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='HTML'
        )