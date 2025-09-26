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
        5: "attachments_optional",
        6: "confirmation"
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

async def handle_photo_attachment(user_id: int, photo, username: str):
    """
    Processa anexo de foto durante o formulário de suporte.
    """
    try:
        # Verifica se está em conversa de suporte ativa
        conversation = get_support_conversation(user_id)
        if not conversation:
            await send_photo_not_in_support(user_id)
            return False

        current_step = conversation['current_step']
        form_data = json.loads(conversation['form_data'] or '{}')

        # Só aceita fotos no passo 5 (anexos) e se estiver aguardando imagens
        if current_step != 5 or not form_data.get('waiting_for_images'):
            await send_photo_not_expected(user_id)
            return False

        # Verifica limite de anexos (máximo 3)
        attachments = form_data.get('attachments', [])
        if len(attachments) >= 3:
            await send_max_attachments_reached(user_id)
            return False

        # Processa a imagem
        await process_photo_attachment(user_id, photo, form_data, username)
        return True

    except Exception as e:
        logger.error(f"Erro ao processar anexo de foto de {username}: {e}")
        return False

async def process_photo_attachment(user_id: int, photo, form_data: dict, username: str):
    """Processa e salva anexo de foto"""
    try:
        from telegram import Bot
        import os
        import tempfile

        # Download da foto
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            file = await bot.get_file(photo.file_id)

            # Cria diretório temporário se não existir
            temp_dir = os.path.join(tempfile.gettempdir(), 'sentinela_attachments')
            os.makedirs(temp_dir, exist_ok=True)

            # Nome do arquivo baseado no user_id e timestamp
            file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
            filename = f"attachment_{user_id}_{len(form_data.get('attachments', []))+1}.{file_extension}"
            file_path = os.path.join(temp_dir, filename)

            # Download do arquivo
            await file.download_to_drive(file_path)

        # Adiciona aos anexos
        attachments = form_data.get('attachments', [])
        attachments.append({
            'file_id': photo.file_id,
            'file_path': file_path,
            'filename': filename,
            'file_size': photo.file_size
        })
        form_data['attachments'] = attachments

        # Atualiza conversa
        update_support_conversation(user_id, 5, 'attachments_optional', json.dumps(form_data))

        # Confirma recebimento
        await send_photo_received_confirmation(user_id, len(attachments))

    except Exception as e:
        logger.error(f"Erro ao processar foto de {username}: {e}")
        await send_photo_processing_error(user_id)

async def send_photo_not_in_support(user_id: int):
    """Informa que não está em processo de suporte"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text="📸 Foto recebida, mas você não está em processo de criação de atendimento.\n\n"
                     "Use /suporte para iniciar um novo atendimento.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de foto fora de suporte: {e}")

async def send_photo_not_expected(user_id: int):
    """Informa que não é o momento de enviar fotos"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text="📸 Foto recebida, mas não é o momento de anexar imagens.\n\n"
                     "Complete o formulário atual primeiro.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de foto não esperada: {e}")

async def send_max_attachments_reached(user_id: int):
    """Informa que atingiu limite de anexos"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text="📎 <b>Limite de anexos atingido!</b>\n\n"
                     "Você já anexou 3 imagens (limite máximo).\n\n"
                     "Clique em <b>'Finalizar anexos'</b> para continuar.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de limite de anexos: {e}")

async def send_photo_received_confirmation(user_id: int, total_attachments: int):
    """Confirma recebimento da foto"""
    try:
        remaining = 3 - total_attachments
        message = (
            f"✅ <b>Imagem {total_attachments}/3 recebida!</b>\n\n"
            f"📎 Total de anexos: {total_attachments}\n"
        )

        if remaining > 0:
            message += f"📤 Você pode enviar mais {remaining} imagem(ns) ou clicar em 'Finalizar anexos'."
        else:
            message += f"🔥 Limite máximo atingido! Clique em 'Finalizar anexos' para continuar."

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro ao enviar confirmação de foto: {e}")

async def send_photo_processing_error(user_id: int):
    """Informa erro no processamento da foto"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text="❌ <b>Erro ao processar imagem</b>\n\n"
                     "Ocorreu um erro ao salvar sua imagem. Tente enviar novamente ou continue sem anexos.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de erro de processamento: {e}")

async def process_hubsoft_attachments(hubsoft_id: str, attachments: list, username: str):
    """Processa e envia anexos para o HubSoft"""
    try:
        from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
        import os

        logger.info(f"Enviando {len(attachments)} anexo(s) para HubSoft - atendimento {hubsoft_id}")

        for i, attachment in enumerate(attachments, 1):
            try:
                file_path = attachment.get('file_path')
                filename = attachment.get('filename', f'anexo_{i}.jpg')

                if not file_path or not os.path.exists(file_path):
                    logger.warning(f"Arquivo não encontrado: {file_path}")
                    continue

                # Lê o arquivo
                with open(file_path, 'rb') as file:
                    file_content = file.read()

                # Envia para HubSoft
                success = await hubsoft_atendimento_client.add_attachment_to_atendimento(
                    hubsoft_id,
                    file_content,
                    filename
                )

                if success:
                    logger.info(f"Anexo {i} enviado com sucesso: {filename}")
                else:
                    logger.warning(f"Falha ao enviar anexo {i}: {filename}")

                # Remove arquivo temporário após envio
                try:
                    os.remove(file_path)
                    logger.debug(f"Arquivo temporário removido: {file_path}")
                except Exception as remove_error:
                    logger.warning(f"Erro ao remover arquivo temporário {file_path}: {remove_error}")

            except Exception as attachment_error:
                logger.error(f"Erro ao processar anexo {i} para {username}: {attachment_error}")

        logger.info(f"Processamento de anexos concluído para atendimento {hubsoft_id}")

    except Exception as e:
        logger.error(f"Erro geral ao processar anexos HubSoft para {username}: {e}")

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
        elif current_step == 5:  # Anexos opcionais
            await process_attachments_step(user_id, action, form_data, username)
        elif current_step == 6:  # Confirmação
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
            progress_text = "🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓░░░░░] 1/6\n\n✅ Iniciado\n🔄 Tipo do problema...\n⏳ Jogo afetado...\n⏳ Quando começou...\n⏳ Detalhes...\n⏳ Anexos (opcional)...\n⏳ Confirmação..."
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
            progress_text = "🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓░░░░] 2/6\n\n✅ Tipo do problema: " + form_data['category_name'] + "\n🔄 Jogo afetado...\n⏳ Quando começou...\n⏳ Detalhes...\n⏳ Anexos (opcional)...\n⏳ Confirmação..."
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
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓░░░] 3/6\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n🔄 Quando começou...\n⏳ Detalhes...\n⏳ Anexos (opcional)...\n⏳ Confirmação..."
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
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓▓░░] 4/6\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n✅ Quando começou: {form_data['timing_name']}\n🔄 Coletando detalhes...\n⏳ Anexos (opcional)...\n⏳ Confirmação..."
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

        # Atualiza conversa para anexos (passo 5)
        update_support_conversation(user_id, 5, 'attachments_optional', json.dumps(form_data))

        # Vai para passo de anexos opcionais
        await send_attachments_step(user_id, form_data, username)

    except Exception as e:
        logger.error(f"Erro ao processar descrição para {username}: {e}")

async def send_attachments_step(user_id: int, form_data: dict, username: str):
    """Envia passo opcional de anexos"""
    try:
        attachments_text = (
            f"📎 <b>ANEXOS OPCIONAIS</b>\n\n"
            f"Você pode enviar imagens que ajudem nossa equipe técnica a entender melhor o problema:\n\n"
            f"📱 <b>Tipos úteis de imagem:</b>\n"
            f"• 📊 Print do speedtest\n"
            f"• 🎮 Screenshot do jogo com ping/lag\n"
            f"• ⚙️ Tela de configurações de rede\n"
            f"• 🖥️ Monitor de rede/task manager\n"
            f"• 📋 Mensagens de erro\n\n"
            f"📎 <b>Como anexar:</b>\n"
            f"• Envie as imagens diretamente neste chat\n"
            f"• Máximo de 3 imagens\n"
            f"• Formatos aceitos: JPG, PNG\n\n"
            f"⚡️ Isso é <b>opcional</b> - você pode pular se preferir!"
        )

        keyboard = create_attachments_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=attachments_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

            # Progress bar para anexos
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓▓▓░] 5/6\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n✅ Quando começou: {form_data['timing_name']}\n✅ Detalhes coletados\n🔄 Anexos (opcional)...\n⏳ Confirmação..."
            await bot.send_message(
                chat_id=user_id,
                text=progress_text,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Erro ao enviar passo de anexos para {username}: {e}")

async def process_attachments_step(user_id: int, action: str, form_data: dict, username: str):
    """Processa passo de anexos"""
    try:
        if action == "skip_attachments":
            # Pula anexos e vai para confirmação
            form_data['attachments'] = []
            update_support_conversation(user_id, 6, 'confirmation', json.dumps(form_data))
            await send_confirmation_summary(user_id, form_data, username)
        elif action == "add_attachments":
            # Configura para receber imagens
            form_data['waiting_for_images'] = True
            form_data['attachments'] = []
            update_support_conversation(user_id, 5, 'attachments_optional', json.dumps(form_data))
            await send_waiting_for_images(user_id)
        elif action == "finalize_attachments":
            # Finaliza anexos e vai para confirmação
            form_data.pop('waiting_for_images', None)
            update_support_conversation(user_id, 6, 'confirmation', json.dumps(form_data))
            await send_confirmation_summary(user_id, form_data, username)

    except Exception as e:
        logger.error(f"Erro ao processar anexos para {username}: {e}")

async def send_waiting_for_images(user_id: int):
    """Informa que está aguardando imagens"""
    try:
        waiting_text = (
            f"📸 <b>AGUARDANDO SUAS IMAGENS</b>\n\n"
            f"Envie até <b>3 imagens</b> uma de cada vez.\n\n"
            f"📎 Depois de enviar todas as imagens, clique em <b>'Finalizar Anexos'</b> para continuar.\n\n"
            f"⚠️ <b>Importante:</b> Envie apenas imagens (JPG/PNG)"
        )

        keyboard = create_finalize_attachments_keyboard()

        bot = Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=user_id,
                text=waiting_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Erro ao enviar aguardando imagens: {e}")

def create_attachments_keyboard():
    """Cria teclado para escolha de anexos"""
    keyboard = [
        [InlineKeyboardButton("📎 Sim, vou anexar imagens", callback_data="support_add_attachments")],
        [InlineKeyboardButton("⏭️ Pular anexos e continuar", callback_data="support_skip_attachments")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_finalize_attachments_keyboard():
    """Cria teclado para finalizar anexos"""
    keyboard = [
        [InlineKeyboardButton("✅ Finalizar anexos e continuar", callback_data="support_finalize_attachments")],
        [InlineKeyboardButton("❌ Cancelar anexos", callback_data="support_skip_attachments")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_confirmation_summary(user_id: int, form_data: dict, username: str):
    """Envia resumo para confirmação"""
    try:
        # Busca dados do usuário
        user_data = get_user_data(user_id)
        client_name = user_data.get('client_name', 'Cliente') if user_data else 'Cliente'

        # Trunca descrição para resumo
        description_preview = form_data['description'][:100] + "..." if len(form_data['description']) > 100 else form_data['description']

        # Informações sobre anexos
        attachments = form_data.get('attachments', [])
        attachments_info = ""
        if attachments:
            attachments_info = f"📎 <b>Anexos:</b> {len(attachments)} imagem(ns) anexada(s)\n"
        else:
            attachments_info = f"📎 <b>Anexos:</b> Nenhum anexo\n"

        summary_text = (
            f"✅ <b>RESUMO DO SEU ATENDIMENTO:</b>\n\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"🎮 <b>Problema:</b> {form_data['category_name']}\n"
            f"🎯 <b>Jogo:</b> {form_data['game_name']}\n"
            f"⏰ <b>Iniciado:</b> {form_data['timing_name']}\n"
            f"📝 <b>Detalhes:</b> \"{description_preview}\"\n"
            f"{attachments_info}\n"
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
            attachments_status = f"✅ Anexos: {len(form_data.get('attachments', []))} imagem(ns)" if form_data.get('attachments') else "✅ Anexos: Nenhum"
            progress_text = f"🎯 <b>CRIANDO SEU ATENDIMENTO</b> [▓▓▓▓▓▓] 6/6\n\n✅ Tipo do problema: {form_data['category_name']}\n✅ Jogo afetado: {form_data['game_name']}\n✅ Quando começou: {form_data['timing_name']}\n✅ Detalhes coletados\n{attachments_status}\n🔄 Aguardando confirmação..."
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
        from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
        from src.sentinela.integrations.hubsoft.config import format_protocol

        # Busca dados do cliente
        user_data = get_user_data(user_id)
        if not user_data:
            await send_error_message(user_id, "Erro: dados do cliente não encontrados")
            return

        # Monta dados do ticket para HubSoft
        ticket_data = {
            'user_id': user_id,
            'username': username,
            'user_mention': f"@{username}",
            'cpf': user_data.get('cpf', ''),
            'client_name': user_data.get('client_name', ''),
            'category': form_data['category'],
            'affected_game': form_data['game'],
            'problem_started': form_data['timing'],
            'description': form_data['description'],
            'urgency_level': calculate_urgency(form_data),
            'topic_thread_id': 148  # ID do tópico de suporte
        }

        # Tenta criar atendimento no HubSoft primeiro
        hubsoft_id = None
        protocol = None
        hubsoft_success = False

        try:
            logger.info(f"Criando atendimento HubSoft para usuário {username}")
            hubsoft_response = await hubsoft_atendimento_client.create_atendimento(
                client_cpf=user_data.get('cpf', ''),
                ticket_data=ticket_data
            )

            # Usa estrutura correta da resposta da API
            if hubsoft_response:
                hubsoft_id = hubsoft_response.get('id_atendimento')
                protocol = hubsoft_response.get('protocolo')

                if hubsoft_id and protocol:
                    hubsoft_success = True
                    logger.info(f"Atendimento HubSoft criado com sucesso: ID {hubsoft_id}, Protocolo: {protocol}")

                    # Salva no banco local com ID do HubSoft
                    ticket_data['hubsoft_atendimento_id'] = hubsoft_id
                    ticket_data['protocolo'] = protocol
                    ticket_id = save_support_ticket(ticket_data)

                    # Adiciona mensagem inicial com contexto enriquecido do bot
                    attachments_info = ""
                    attachments = form_data.get('attachments', [])
                    if attachments:
                        attachments_info = f"• Anexos: {len(attachments)} imagem(ns) anexada(s)\n"

                    await hubsoft_atendimento_client.add_message_to_atendimento(
                        str(hubsoft_id),
                        f"🤖 Bot Telegram OnCabo: Atendimento criado via formulário conversacional interativo.\n\n"
                        f"📱 Dados da sessão:\n"
                        f"• User: @{username} (ID: {user_id})\n"
                        f"• Categoria: {SupportFormManager.CATEGORIES.get(form_data['category'], form_data['category'])}\n"
                        f"• Jogo: {SupportFormManager.POPULAR_GAMES.get(form_data['game'], form_data['game'])}\n"
                        f"• Timing: {SupportFormManager.TIMING_OPTIONS.get(form_data['timing'], form_data['timing'])}\n"
                        f"• Urgência: {calculate_urgency(form_data)}\n"
                        f"{attachments_info}"
                        f"• Concluído: {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                        f"🎯 Cliente guiado através do formulário inteligente para coleta precisa de informações."
                    )

                    # Envia anexos para o HubSoft se existirem
                    if attachments:
                        await process_hubsoft_attachments(str(hubsoft_id), attachments, username)
                else:
                    raise Exception("Resposta da API sem ID ou protocolo válido")
            else:
                raise Exception("Resposta vazia da API HubSoft")

        except Exception as hubsoft_error:
            logger.error(f"Erro ao criar atendimento no HubSoft: {hubsoft_error}")

            # Fallback: salva apenas localmente
            logger.info("Salvando ticket apenas no banco local como fallback")
            ticket_id = save_support_ticket(ticket_data)
            protocol = f"ATD{ticket_id:06d}" if ticket_id else "ERRO"
            hubsoft_success = False

        # Se não conseguiu criar no HubSoft, usa fallback local
        if not hubsoft_success:
            logger.warning(f"Atendimento salvo apenas localmente como fallback: {protocol}")

        # Envia notificação para canal técnico
        await notify_tech_team_new_ticket(ticket_data, user_data, protocol)

        # Envia confirmação para o usuário
        await send_ticket_created_success(user_id, protocol, form_data, user_data)

        logger.info(f"Ticket de suporte criado com sucesso: {protocol}")

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
            f"📋 <b>Protocolo:</b> {protocol}\n"
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
            f"• Mencione o protocolo {protocol}\n"
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