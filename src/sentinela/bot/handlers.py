import logging
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler

# Importa o serviço de usuário para ser usado no handler
from src.sentinela.services import user_service
from src.sentinela.services.welcome_service import handle_new_member, handle_rules_button, should_bot_respond_in_topic
from src.sentinela.services.topics_service import topics_service
from src.sentinela.services.topics_discovery import scan_group_for_topics, get_group_real_info
from src.sentinela.services.cpf_verification_service import CPFVerificationService

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /start. Envia uma mensagem de boas-vindas OnCabo Gamer.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Ignora comandos no grupo
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /start ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /start recebido de {user.username} (ID: {user.id}) no chat privado")
    await update.message.reply_html(
        f"🎮 Olá, {user.mention_html()}!\n\n"
        f"🔥 Bem-vindo à <b>OnCabo</b>! 🔥\n\n"
        f"Obrigado por escolher o <b>Plano Gamer</b> - a internet que todo gamer merece! 🚀\n\n"
        f"🎯 Para acessar nossa <b>Comunidade Gamer exclusiva</b> no Telegram, preciso verificar seu contrato.\n\n"
        f"📝 Por favor, envie seu <b>CPF</b> para validarmos seu acesso:"
    )

async def test_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /test_group. Testa o acesso ao grupo configurado.
    Funciona apenas em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID
    from telegram import Bot

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Ignora comandos no grupo
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /test_group ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /test_group recebido de {user.username} (ID: {user.id}) no chat privado")

    try:
        bot = Bot(token=context.bot.token)

        # Tenta obter informações do grupo
        chat_info = await bot.get_chat(TELEGRAM_GROUP_ID)

        response = (
            f"✅ TESTE DE GRUPO - SUCESSO\n\n"
            f"🆔 ID: {TELEGRAM_GROUP_ID}\n"
            f"📝 Nome: {chat_info.title}\n"
            f"👥 Tipo: {chat_info.type}\n"
            f"📊 Membros: {chat_info.get_member_count()}\n\n"
            f"🔧 Status: Bot tem acesso ao grupo!"
        )

    except Exception as e:
        logger.error(f"Erro no teste do grupo: {e}")
        response = (
            f"❌ TESTE DE GRUPO - FALHA\n\n"
            f"🆔 ID Configurado: {TELEGRAM_GROUP_ID}\n"
            f"⚠️ Erro: {str(e)}\n\n"
            f"Possíveis soluções:\n"
            f"• Verificar se o ID do grupo está correto\n"
            f"• Adicionar o bot como admin no grupo\n"
            f"• Conceder permissão 'Convidar usuários'"
        )

    await update.message.reply_text(response)


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /topics - Lista todos os tópicos descobertos no grupo.
    Funciona apenas em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Só funciona em chat privado
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /topics ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /topics recebido de {user.username} (ID: {user.id})")

    try:
        # Gera lista de tópicos
        topics_list = await topics_service.format_topics_list()

        await update.message.reply_html(topics_list)

    except Exception as e:
        logger.error(f"Erro no comando topics: {e}")
        await update.message.reply_text(
            "❌ Erro ao listar tópicos. Verifique os logs do bot."
        )

async def auto_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /auto_config - Sugere configurações automáticas de tópicos.
    Funciona apenas em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Só funciona em chat privado
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /auto_config ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /auto_config recebido de {user.username} (ID: {user.id})")

    try:
        # Gera configuração automática
        config_suggestions = await topics_service.auto_configure_topics()

        await update.message.reply_html(config_suggestions)

    except Exception as e:
        logger.error(f"Erro no comando auto_config: {e}")
        await update.message.reply_text(
            "❌ Erro ao gerar configuração automática. Verifique os logs do bot."
        )

async def test_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /test_topics - Testa a configuração atual de tópicos.
    Funciona apenas em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID, RULES_TOPIC_ID, WELCOME_TOPIC_ID

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Só funciona em chat privado
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /test_topics ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /test_topics recebido de {user.username} (ID: {user.id})")

    try:
        message = "🧪 <b>TESTE DE CONFIGURAÇÃO DE TÓPICOS</b>\n\n"

        # Verifica configurações atuais
        message += "📋 <b>Configuração Atual:</b>\n"
        message += f"• Grupo ID: <code>{TELEGRAM_GROUP_ID}</code>\n"
        message += f"• Tópico Regras: <code>{RULES_TOPIC_ID or 'Não configurado'}</code>\n"
        message += f"• Tópico Boas-vindas: <code>{WELCOME_TOPIC_ID or 'Não configurado'}</code>\n\n"

        # Busca tópicos descobertos
        topics = await topics_service.get_all_topics()
        message += f"🔍 <b>Tópicos Descobertos:</b> {len(topics)}\n\n"

        # Validação
        rules_found = False
        welcome_found = False

        if RULES_TOPIC_ID:
            for topic in topics:
                if str(topic['id']) == str(RULES_TOPIC_ID):
                    rules_found = True
                    message += f"✅ Tópico Regras encontrado: {topic['name']}\n"
                    break
            if not rules_found:
                message += f"❌ Tópico Regras (ID: {RULES_TOPIC_ID}) não encontrado\n"

        if WELCOME_TOPIC_ID:
            for topic in topics:
                if str(topic['id']) == str(WELCOME_TOPIC_ID):
                    welcome_found = True
                    message += f"✅ Tópico Boas-vindas encontrado: {topic['name']}\n"
                    break
            if not welcome_found:
                message += f"❌ Tópico Boas-vindas (ID: {WELCOME_TOPIC_ID}) não encontrado\n"

        message += "\n"

        # Status geral
        if (not RULES_TOPIC_ID and not WELCOME_TOPIC_ID):
            message += "⚠️ <b>Status:</b> Nenhum tópico configurado\n"
            message += "💡 Use /auto_config para sugestões automáticas"
        elif rules_found or welcome_found:
            message += "✅ <b>Status:</b> Configuração funcionando\n"
            message += "🎯 Bot responderá apenas nos tópicos configurados"
        else:
            message += "❌ <b>Status:</b> IDs configurados mas tópicos não encontrados\n"
            message += "🔧 Verifique os IDs ou use /auto_config"

        await update.message.reply_html(message)

    except Exception as e:
        logger.error(f"Erro no comando test_topics: {e}")
        await update.message.reply_text(
            "❌ Erro ao testar configuração. Verifique os logs do bot."
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /status - Consulta status dos atendimentos do cliente.
    Funciona em chat privado e no tópico de suporte do grupo.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID, SUPPORT_TOPIC_ID, HUBSOFT_ENABLED
    from src.sentinela.clients.db_client import get_user_data
    from datetime import datetime

    # Importa HubSoft apenas se habilitado
    if HUBSOFT_ENABLED:
        from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
        from src.sentinela.integrations.hubsoft.config import get_status_display, format_protocol

    user = update.effective_user
    chat_id = update.effective_chat.id
    message_thread_id = getattr(update.message, 'message_thread_id', None)
    is_group_request = False

    # Se for no grupo, verifica se é no tópico de suporte
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        if not SUPPORT_TOPIC_ID or str(message_thread_id) != str(SUPPORT_TOPIC_ID):
            logger.info(f"Comando /status ignorado - tópico incorreto {message_thread_id}")
            return

        # Responde no grupo informando que será enviado no privado
        await update.message.reply_html(
            f"👤 {user.mention_html()}\n\n"
            "📱 <b>Consultando seus atendimentos...</b>\n\n"
            "🔒 As informações serão enviadas no <b>chat privado</b> por questões de privacidade.\n\n"
            "💬 Verifique suas mensagens privadas comigo!"
        )

        # Marca que foi requisição do grupo
        is_group_request = True

    logger.info(f"Comando /status recebido de {user.username} (ID: {user.id})")

    async def send_status_message(content: str):
        """Envia mensagem do status - no privado se foi solicitado do grupo"""
        if is_group_request:
            from src.sentinela.core.config import TELEGRAM_TOKEN
            from telegram import Bot
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(chat_id=user.id, text=content, parse_mode='HTML')
        else:
            await update.message.reply_html(content)

    try:
        # Busca dados do usuário
        user_data = get_user_data(user.id)
        if not user_data:
            await send_status_message(
                "❌ <b>Cliente não encontrado</b>\n\n"
                "Para consultar seus atendimentos, você precisa ser um cliente OnCabo verificado.\n\n"
                "📝 Use o comando /start para validar seu CPF primeiro."
            )
            return

        client_cpf = user_data.get('cpf')
        if not client_cpf:
            await send_status_message(
                "❌ <b>CPF não encontrado</b>\n\n"
                "Não foi possível localizar seu CPF no sistema.\n\n"
                "📝 Use o comando /start para revalidar seus dados."
            )
            return

        # Busca IDs dos atendimentos criados pelo bot para este usuário
        from src.sentinela.clients.db_client import get_user_bot_created_hubsoft_ids
        bot_created_ids = get_user_bot_created_hubsoft_ids(user.id)

        if not bot_created_ids:
            await send_status_message(
                "✅ <b>Nenhum atendimento do bot</b>\n\n"
                "🎮 Você não possui atendimentos criados via bot em aberto no momento.\n\n"
                "📞 Se precisar de ajuda, use o comando /suporte para abrir um novo chamado."
            )
            return

        # Se HubSoft estiver habilitado, busca atendimentos e filtra
        atendimentos = []
        if HUBSOFT_ENABLED:
            try:
                # Busca todos os atendimentos no HubSoft e filtra apenas os criados pelo bot
                all_atendimentos = await hubsoft_atendimento_client.get_client_atendimentos(
                    client_cpf=client_cpf,
                    apenas_pendente=True  # Apenas atendimentos ativos
                )

                # Filtra apenas atendimentos criados pelo bot
                for atendimento in all_atendimentos:
                    atendimento_id = str(atendimento.get('id', ''))
                    if atendimento_id in bot_created_ids:
                        atendimentos.append(atendimento)

            except Exception as e:
                logger.error(f"Erro ao consultar HubSoft: {e}")
                await send_status_message(
                    "⚠️ <b>HubSoft temporariamente indisponível</b>\n\n"
                    "🎮 Seus atendimentos existem, mas não conseguimos acessar o status no momento.\n\n"
                    "🔄 Tente novamente em alguns minutos ou contate o suporte."
                )
                return
        else:
            # HubSoft desabilitado - mostra apenas info local
            await send_status_message(
                "ℹ️ <b>Modo local ativo</b>\n\n"
                f"🎮 Você possui {len(bot_created_ids)} atendimento(s) registrado(s) localmente.\n\n"
                "💡 <b>Observação:</b> HubSoft não está configurado. Seus tickets estão salvos apenas localmente.\n\n"
                "📞 Para abrir um novo chamado, use o comando /suporte."
            )
            return

        if not atendimentos:
            await send_status_message(
                "ℹ️ <b>Atendimentos do bot finalizados</b>\n\n"
                "🎮 Seus atendimentos criados via bot já foram finalizados ou não estão mais pendentes.\n\n"
                "💡 <b>Observação:</b> Este comando mostra apenas atendimentos abertos via /suporte no bot.\n\n"
                "📞 Para abrir um novo chamado, use o comando /suporte."
            )
            return

        # Monta mensagem com lista de atendimentos
        message = "🎮 <b>SEUS ATENDIMENTOS ONCABO (BOT)</b>\n\n"
        message += f"💡 <b>Exibindo apenas atendimentos criados via /suporte no bot</b>\n"
        message += f"📊 <b>Total encontrados:</b> {len(atendimentos)}\n\n"

        for atendimento in atendimentos[:5]:  # Máximo 5 atendimentos
            # Usa protocolo oficial da API ou formata se não houver
            if HUBSOFT_ENABLED:
                protocol = atendimento.get('protocolo') or format_protocol(atendimento.get('id'))
            else:
                protocol = f"LOC{atendimento.get('id', 0):06d}"
            titulo = atendimento.get('titulo') or atendimento.get('tipo_atendimento', 'Suporte Gaming')
            data_cadastro = atendimento.get('data_cadastro', '')

            # Formata data
            try:
                if data_cadastro:
                    dt = datetime.fromisoformat(data_cadastro.replace('Z', '+00:00'))
                    data_formatada = dt.strftime("%d/%m/%Y às %H:%M")
                else:
                    data_formatada = "Data não disponível"
            except:
                data_formatada = "Data não disponível"

            # Status com emoji
            status_info = atendimento.get('status_display', {})
            status_emoji = status_info.get('emoji', '❓')
            status_name = status_info.get('name', 'Status Desconhecido')
            status_message = status_info.get('message', 'Sem informações')

            message += f"📋 <b>{protocol}</b> - {titulo[:30]}{'...' if len(titulo) > 30 else ''}\n"
            message += f"{status_emoji} <b>Status:</b> {status_name}\n"
            message += f"📅 <b>Aberto:</b> {data_formatada}\n"
            message += f"💬 {status_message}\n\n"

        # Adiciona rodapé
        if len(atendimentos) > 5:
            message += f"➕ <i>E mais {len(atendimentos) - 5} atendimentos...</i>\n\n"

        message += (
            "🔄 <b>Dica:</b> Os status são atualizados automaticamente.\n"
            "📞 Para novo atendimento, use /suporte"
        )

        await send_status_message(message)

    except Exception as e:
        logger.error(f"Erro ao processar comando /status para {user.username}: {e}")
        await send_status_message(
            "❌ <b>Erro ao consultar atendimentos</b>\n\n"
            "Ocorreu um erro ao buscar seus chamados. Tente novamente em alguns minutos.\n\n"
            "📞 Se o problema persistir, use /suporte para abrir um novo chamado."
        )

async def suporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /suporte - Inicia processo de abertura de chamado de suporte.
    Funciona tanto no grupo (tópico específico) quanto em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID, SUPPORT_TOPIC_ID
    from src.sentinela.services.support_service import handle_support_request

    user = update.effective_user
    chat_id = update.effective_chat.id
    message_thread_id = getattr(update.message, 'message_thread_id', None)

    logger.info(f"Comando /suporte recebido de {user.username} (ID: {user.id}) no chat {chat_id}")

    # Se for no grupo, verifica se é no tópico de suporte
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        if not SUPPORT_TOPIC_ID or str(message_thread_id) != str(SUPPORT_TOPIC_ID):
            logger.info(f"Comando /suporte ignorado - tópico incorreto {message_thread_id}")
            return

        # Responde no grupo e inicia no privado
        await update.message.reply_html(
            f"🎮 <b>{user.mention_html()}</b>, estou te chamando no privado para abrir seu chamado de suporte!\n\n"
            f"📱 Verifique suas mensagens privadas comigo para preencher o formulário."
        )

    # Processa a solicitação de suporte
    await handle_support_request(user.id, user.username, user.mention_html())

async def scan_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /scan_topics - Força descoberta de tópicos via API.
    Funciona apenas em chat privado.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Só funciona em chat privado
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /scan_topics ignorado no grupo {chat_id}")
        return

    logger.info(f"Comando /scan_topics recebido de {user.username} (ID: {user.id})")

    try:
        await update.message.reply_text("🔍 <b>Escaneando grupo...</b>", parse_mode='HTML')

        # Obtém info do grupo
        group_info = await get_group_real_info()

        # Escaneia tópicos
        topics = await scan_group_for_topics()

        message = f"📊 <b>RESULTADO DO SCAN</b>\n\n"
        message += f"🏠 <b>Grupo:</b> {group_info.get('title', 'N/A')}\n"
        message += f"🆔 <b>ID:</b> <code>{group_info.get('id', 'N/A')}</code>\n"
        message += f"👥 <b>Tipo:</b> {group_info.get('type', 'N/A')}\n"
        message += f"📊 <b>Membros:</b> {group_info.get('member_count', 'N/A')}\n"
        message += f"📋 <b>Suporte a tópicos:</b> {'✅' if group_info.get('has_topics') else '❌'}\n\n"

        if topics:
            message += f"🔍 <b>TÓPICOS ENCONTRADOS:</b> {len(topics)}\n\n"
            for i, topic in enumerate(topics, 1):
                message += f"{i}. <b>{topic['name']}</b>\n"
                message += f"   🆔 ID: <code>{topic['id']}</code>\n"
                if topic['last_message']:
                    message += f"   💬 Última msg: {topic['last_message']}...\n"
                message += "\n"

            message += "🔧 <b>Para configurar:</b>\n"
            message += "• Copie o ID desejado\n"
            message += "• Adicione no .env:\n"
            message += "• <code>RULES_TOPIC_ID=\"ID_AQUI\"</code>\n"
            message += "• <code>WELCOME_TOPIC_ID=\"ID_AQUI\"</code>"
        else:
            message += "❌ <b>NENHUM TÓPICO ENCONTRADO</b>\n\n"
            message += "💡 <b>Possíveis motivos:</b>\n"
            message += "• Grupo não tem tópicos configurados\n"
            message += "• Bot não tem histórico de mensagens\n"
            message += "• Tópicos não têm mensagens recentes\n\n"
            message += "🔧 <b>Soluções:</b>\n"
            message += "• Crie tópicos no grupo\n"
            message += "• Envie mensagens nos tópicos\n"
            message += "• Use /topics depois de atividade"

        await update.message.reply_html(message)

    except Exception as e:
        logger.error(f"Erro no comando scan_topics: {e}")
        await update.message.reply_text(
            f"❌ Erro ao escanear grupo: {str(e)}"
        )

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para mensagens no grupo - responde apenas em tópicos específicos.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID

    chat_id = update.effective_chat.id
    message = update.message

    # Verifica se é no grupo configurado
    if str(chat_id) != str(TELEGRAM_GROUP_ID):
        return

    # Descobre tópicos automaticamente (sempre que há mensagem no grupo)
    await topics_service.discover_topics_from_messages(update)

    # Verifica se há novos membros
    if message.new_chat_members:
        await handle_new_member(update)
        return

    # Verifica se deve responder neste tópico
    message_thread_id = getattr(message, 'message_thread_id', None)
    if not should_bot_respond_in_topic(message_thread_id):
        logger.debug(f"Mensagem ignorada - tópico {message_thread_id} não autorizado")
        return

    # Aqui você pode adicionar lógica específica para responder em tópicos
    logger.info(f"Mensagem recebida no tópico autorizado {message_thread_id}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para callback queries (botões inline).
    """
    from src.sentinela.services.support_service import handle_support_callback

    query = update.callback_query
    user = query.from_user

    logger.info(f"Callback query recebido: {query.data} de {user.username}")

    if query.data.startswith("accept_rules_"):
        await handle_rules_button(update)
    elif query.data.startswith("support_"):
        # Processa botões do formulário de suporte
        support_handled = await handle_support_callback(user.id, query.data, user.username)
        if support_handled:
            await query.answer()  # Confirma o clique
        else:
            await query.answer("Erro ao processar solicitação")
    elif query.data == "cpf_verification_cancel":
        # Cancela verificação de CPF
        await handle_cpf_verification_cancel(query)
    else:
        # Outros botões podem ser adicionados aqui
        await query.answer("Botão não reconhecido")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para mensagens de texto.
    - Primeira interação: Boas-vindas para qualquer mensagem
    - Interações seguintes: Aceita apenas CPF válido
    - Durante formulário de suporte: Processa passos do formulário
    """
    from src.sentinela.utils.cpf_validator import extract_cpf_from_message, is_message_cpf_only
    from src.sentinela.core.config import TELEGRAM_GROUP_ID
    from src.sentinela.clients.db_client import is_first_interaction, mark_user_interacted
    from src.sentinela.services.support_service import handle_support_message

    message_text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Verifica se é uma mensagem no grupo - ignora
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Mensagem ignorada no grupo {chat_id}")
        return

    logger.info(f"Mensagem de texto recebida de {user.username} no chat privado.")

    # Verifica se é parte do formulário de suporte
    support_handled = await handle_support_message(user.id, message_text, user.username)
    if support_handled:
        return  # Mensagem foi processada pelo sistema de suporte

    # Verifica se há verificação de CPF pendente
    pending_verification = CPFVerificationService.get_pending_verification(user.id)
    if pending_verification:
        await handle_cpf_verification_response(update, user.id, user.username, message_text)
        return

    # Verifica se é primeira interação
    if is_first_interaction(user.id):
        logger.info(f"Primeira interação de {user.username} (ID: {user.id})")

        # Verifica se já enviou um CPF na primeira mensagem
        cpf = extract_cpf_from_message(message_text)

        if cpf and is_message_cpf_only(message_text):
            # Primeira mensagem JÁ é um CPF válido - processa direto
            logger.info(f"CPF válido detectado na primeira interação: {user.username}")
            mark_user_interacted(user.id)

            # Processa o CPF imediatamente
            await update.message.reply_html("🔍 <b>CPF recebido!</b> Verificando seu contrato, aguarde um momento...")

            response_message = await user_service.process_user_verification(
                cpf=cpf,
                user_id=user.id,
                username=user.username
            )

            await update.message.reply_html(response_message)
            return

        # Se não for CPF válido, envia boas-vindas e marca como interagido
        mark_user_interacted(user.id)

        await update.message.reply_html(
            f"🎮 Olá, {user.mention_html()}!\n\n"
            f"🔥 Bem-vindo à <b>OnCabo</b>! 🔥\n\n"
            f"Obrigado por escolher o <b>Plano Gamer</b> - a internet que todo gamer merece! 🚀\n\n"
            f"🎯 Para acessar nossa <b>Comunidade Gamer exclusiva</b> no Telegram, preciso verificar seu contrato.\n\n"
            f"📝 Por favor, envie seu <b>CPF</b> para validarmos seu acesso:"
        )
        return

    # Não é primeira interação - valida CPF rigorosamente
    cpf = extract_cpf_from_message(message_text)

    if not cpf or not is_message_cpf_only(message_text):
        # Não é um CPF válido - orienta o usuário
        await update.message.reply_html(
            f"❌ <b>Formato inválido!</b>\n\n"
            f"🎯 Para acessar a <b>Comunidade Gamer OnCabo</b>, preciso que você envie <b>apenas seu CPF</b>.\n\n"
            f"📝 <b>Formato aceito:</b>\n"
            f"• 123.456.789-01\n"
            f"• 12345678901\n\n"
            f"🔄 Tente novamente enviando apenas seu CPF:"
        )
        return

    # CPF válido encontrado - processa
    await update.message.reply_html("🔍 <b>CPF recebido!</b> Verificando seu contrato, aguarde um momento...")

    # Chama o serviço com os dados do usuário e o CPF
    response_message = await user_service.process_user_verification(
        cpf=cpf,
        user_id=user.id,
        username=user.username
    )

    # Envia a resposta do serviço (sucesso ou falha) de volta para o usuário
    await update.message.reply_html(response_message)

async def handle_cpf_verification_response(update: Update, user_id: int, username: str, message_text: str):
    """Handler para processar respostas de verificação de CPF"""
    try:
        from src.sentinela.utils.cpf_validator import extract_cpf_from_message, is_message_cpf_only

        # Extrai CPF da mensagem
        cpf = extract_cpf_from_message(message_text)

        if not cpf or not is_message_cpf_only(message_text):
            await update.message.reply_html(
                f"❌ <b>Formato de CPF inválido!</b>\n\n"
                f"📝 <b>Envie apenas seu CPF:</b>\n"
                f"• Formato: 12345678901\n"
                f"• Ou: 123.456.789-01\n\n"
                f"🔄 Tente novamente:"
            )
            return

        # Mostra mensagem de processamento
        await update.message.reply_html("🔍 <b>Verificando CPF...</b> Aguarde um momento...")

        # Processa verificação
        result = await CPFVerificationService.process_cpf_verification(user_id, username, cpf)

        # Busca dados da verificação para saber o tipo
        verification = CPFVerificationService.get_pending_verification(user_id)
        verification_type = verification['verification_type'] if verification else "auto_checkup"

        # Envia resultado
        await CPFVerificationService.send_verification_result(user_id, result, verification_type)

        # Se foi bem-sucedida e era para suporte, orienta uso do /suporte
        if result['success'] and verification_type == "support_request":
            await update.message.reply_html(
                f"🎮 <b>Agora você pode usar o suporte!</b>\n\n"
                f"Digite /suporte para abrir seu chamado."
            )

    except Exception as e:
        logger.error(f"Erro ao processar resposta de verificação de CPF para {user_id}: {e}")
        await update.message.reply_html(
            f"❌ <b>Erro interno</b>\n\n"
            f"Ocorreu um erro ao processar seu CPF. Tente novamente mais tarde."
        )

async def handle_cpf_verification_cancel(query):
    """Handler para cancelamento de verificação de CPF"""
    try:
        user_id = query.from_user.id
        username = query.from_user.username

        # Busca verificação pendente
        verification = CPFVerificationService.get_pending_verification(user_id)

        if verification:
            verification_type = verification['verification_type']

            # Marca como cancelada
            CPFVerificationService.complete_verification(
                user_id, False, None, "user_cancelled"
            )

            if verification_type == "support_request":
                message = (
                    f"❌ <b>Verificação cancelada</b>\n\n"
                    f"Você cancelou a verificação de CPF.\n\n"
                    f"🔄 Para usar o suporte, digite /suporte novamente quando quiser confirmar seus dados."
                )
            else:  # auto_checkup
                message = (
                    f"❌ <b>Verificação cancelada</b>\n\n"
                    f"Você cancelou a verificação de CPF.\n\n"
                    f"⚠️ <b>Atenção:</b> Se não confirmar seus dados em 24 horas desde o primeiro aviso, "
                    f"será removido do grupo automaticamente.\n\n"
                    f"📝 Digite seu CPF quando quiser confirmar."
                )

            await query.edit_message_text(message, parse_mode='HTML')
            logger.info(f"Verificação de CPF cancelada pelo usuário {username} (ID: {user_id})")
        else:
            await query.edit_message_text(
                f"❌ <b>Nenhuma verificação encontrada</b>\n\n"
                f"Não há verificação pendente para cancelar.",
                parse_mode='HTML'
            )

        await query.answer("Verificação cancelada")

    except Exception as e:
        logger.error(f"Erro ao cancelar verificação de CPF: {e}")
        await query.answer("Erro ao cancelar verificação")


async def admin_tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /admin_tickets - Consulta avançada de tickets para administradores.
    Funciona apenas em chat privado e para usuários autorizados.
    """
    from src.sentinela.core.config import TELEGRAM_GROUP_ID, ADMIN_USER_IDS
    from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
    from datetime import datetime, timedelta

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Só funciona em chat privado
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Comando /admin_tickets ignorado no grupo {chat_id}")
        return

    # Verifica se usuário é admin
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_html("❌ <b>Acesso negado</b>\n\nEste comando é restrito a administradores.")
        return

    logger.info(f"Comando /admin_tickets recebido de {user.username} (ID: {user.id})")

    try:
        # Parsear argumentos do comando
        args = context.args
        pagina = 0
        itens_por_pagina = 10
        data_inicio = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        data_fim = datetime.now().strftime('%Y-%m-%d')

        # Processar argumentos opcionais
        if args:
            for arg in args:
                if arg.startswith('pagina='):
                    pagina = max(0, int(arg.split('=')[1]) - 1)  # Usuário usa 1-based, API usa 0-based
                elif arg.startswith('limite='):
                    itens_por_pagina = min(50, max(1, int(arg.split('=')[1])))
                elif arg.startswith('dias='):
                    dias = int(arg.split('=')[1])
                    data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Consulta usando endpoint otimizado
        resultado = await hubsoft_atendimento_client.get_atendimentos_paginado(
            pagina=pagina,
            itens_por_pagina=itens_por_pagina,
            data_inicio=data_inicio,
            data_fim=data_fim,
            relacoes="atendimento_mensagem,cliente_servico"
        )

        if resultado['status'] != 'success':
            await update.message.reply_html(
                f"❌ <b>Erro na consulta:</b> {resultado.get('msg', 'Erro desconhecido')}"
            )
            return

        atendimentos = resultado['atendimentos']
        paginacao = resultado['paginacao']

        if not atendimentos:
            await update.message.reply_html(
                f"📊 <b>CONSULTA ADMINISTRATIVA</b>\n\n"
                f"📅 Período: {data_inicio} a {data_fim}\n"
                f"📄 Página: {pagina + 1}\n\n"
                f"✅ Nenhum atendimento encontrado no período."
            )
            return

        # Monta relatório
        message = f"📊 <b>RELATÓRIO ADMINISTRATIVO DE TICKETS</b>\n\n"
        message += f"📅 <b>Período:</b> {data_inicio} a {data_fim}\n"
        message += f"📄 <b>Página:</b> {pagina + 1} de {paginacao.get('ultima_pagina', 0) + 1}\n"
        message += f"📈 <b>Total:</b> {paginacao.get('total_registros', 0)} tickets\n"
        message += f"📋 <b>Exibindo:</b> {len(atendimentos)} tickets\n\n"
        message += "───────────────────────────────────\n\n"

        for i, atendimento in enumerate(atendimentos, 1):
            protocolo = atendimento.get('protocolo', 'N/A')
            status_info = atendimento.get('status', {})
            status_name = status_info.get('display', 'Status Desconhecido') if isinstance(status_info, dict) else str(status_info)

            # Cliente info
            cliente_info = "Cliente Desconhecido"
            if 'cliente_servico' in atendimento and 'cliente' in atendimento['cliente_servico']:
                cliente_info = atendimento['cliente_servico']['cliente'].get('display', 'Cliente')

            # Tempo em aberto formatado
            tempo_formatado = atendimento.get('tempo_aberto_formatado', 'N/A')

            # Tipo de atendimento
            tipo_info = atendimento.get('tipo_atendimento', {})
            tipo_nome = tipo_info.get('descricao', 'Tipo Desconhecido') if isinstance(tipo_info, dict) else str(tipo_info)

            message += f"<b>{i}. #{protocolo}</b>\n"
            message += f"👤 {cliente_info}\n"
            message += f"🏷️ {tipo_nome}\n"
            message += f"📊 {status_name} | ⏱️ {tempo_formatado}\n\n"

        # Instruções de uso
        message += "───────────────────────────────────\n\n"
        message += "<b>💡 COMANDOS DISPONÍVEIS:</b>\n"
        message += "• <code>/admin_tickets</code> - Esta página\n"
        message += "• <code>/admin_tickets pagina=2</code> - Página específica\n"
        message += "• <code>/admin_tickets limite=20</code> - Mais resultados\n"
        message += "• <code>/admin_tickets dias=30</code> - Últimos 30 dias\n"
        message += "• <code>/admin_tickets pagina=2 limite=5 dias=14</code> - Combinado"

        await update.message.reply_html(message)

    except ValueError as ve:
        await update.message.reply_html(
            f"❌ <b>Erro nos parâmetros:</b> {str(ve)}\n\n"
            f"💡 Uso correto: <code>/admin_tickets pagina=1 limite=10 dias=7</code>"
        )
    except Exception as e:
        logger.error(f"Erro no comando /admin_tickets: {e}")
        await update.message.reply_html(
            "❌ <b>Erro interno</b>\n\n"
            "Ocorreu um erro ao processar a consulta. Verifique os logs do sistema."
        )

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para fotos enviadas em chat privado (anexos de suporte).
    """
    from src.sentinela.services.support_service import handle_photo_attachment

    user = update.effective_user
    photo = update.message.photo[-1]  # Pega a maior resolução

    logger.info(f"Foto recebida de {user.username} (ID: {user.id})")

    # Processa anexo de foto no contexto de suporte
    await handle_photo_attachment(user.id, photo, user.username)

def register_handlers(application: Application) -> None:
    """
    Registra todos os handlers de comando e mensagem na aplicação.
    """
    logger.info("Registrando handlers de comandos e mensagens...")

    # Handlers de comandos (chat privado)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test_group", test_group))
    application.add_handler(CommandHandler("topics", topics_command))
    application.add_handler(CommandHandler("auto_config", auto_config_command))
    application.add_handler(CommandHandler("test_topics", test_topics_command))
    application.add_handler(CommandHandler("scan_topics", scan_topics_command))
    application.add_handler(CommandHandler("suporte", suporte_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("admin_tickets", admin_tickets_command))

    # Handler para callback queries (botões inline)
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Handler para mensagens no grupo (novos membros, tópicos específicos)
    from src.sentinela.core.config import TELEGRAM_GROUP_ID
    group_filter = filters.Chat(chat_id=int(TELEGRAM_GROUP_ID))
    application.add_handler(MessageHandler(group_filter, handle_group_message))

    # Handler para fotos (anexos de suporte) - apenas fora do grupo
    photo_filter = filters.PHOTO & ~group_filter
    application.add_handler(MessageHandler(photo_filter, handle_photo_message))

    # Handler para mensagens privadas (CPF, etc) - apenas fora do grupo
    private_filter = filters.TEXT & ~filters.COMMAND & ~group_filter
    application.add_handler(MessageHandler(private_filter, handle_message))

    logger.info("Handlers registrados com sucesso.")
