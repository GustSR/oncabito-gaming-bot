import logging
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler

# Importa o serviço de usuário para ser usado no handler
from src.sentinela.services import user_service
from src.sentinela.services.welcome_service import handle_new_member, handle_rules_button, should_bot_respond_in_topic
from src.sentinela.services.topics_service import topics_service
from src.sentinela.services.topics_discovery import scan_group_for_topics, get_group_real_info

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
    query = update.callback_query

    if query.data.startswith("accept_rules_"):
        await handle_rules_button(update)
    else:
        # Outros botões podem ser adicionados aqui
        await query.answer("Botão não reconhecido")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para mensagens de texto.
    - Primeira interação: Boas-vindas para qualquer mensagem
    - Interações seguintes: Aceita apenas CPF válido
    """
    from src.sentinela.utils.cpf_validator import extract_cpf_from_message, is_message_cpf_only
    from src.sentinela.core.config import TELEGRAM_GROUP_ID
    from src.sentinela.clients.db_client import is_first_interaction, mark_user_interacted

    message_text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Verifica se é uma mensagem no grupo - ignora
    if str(chat_id) == str(TELEGRAM_GROUP_ID):
        logger.info(f"Mensagem ignorada no grupo {chat_id}")
        return

    logger.info(f"Mensagem de texto recebida de {user.username} no chat privado.")

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

    # Handler para callback queries (botões inline)
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Handler para mensagens no grupo (novos membros, tópicos específicos)
    from src.sentinela.core.config import TELEGRAM_GROUP_ID
    group_filter = filters.Chat(chat_id=int(TELEGRAM_GROUP_ID))
    application.add_handler(MessageHandler(group_filter, handle_group_message))

    # Handler para mensagens privadas (CPF, etc) - apenas fora do grupo
    private_filter = filters.TEXT & ~filters.COMMAND & ~group_filter
    application.add_handler(MessageHandler(private_filter, handle_message))

    logger.info("Handlers registrados com sucesso.")
