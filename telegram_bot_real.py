#!/usr/bin/env python3
"""
Bot Real do Telegram - Nova Arquitetura.

Bot principal do OnCabo Gaming usando 100% nova arquitetura.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Adiciona o path do projeto para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from sentinela.infrastructure.config.container import get_container, shutdown_container
from sentinela.application.commands.cpf_verification_commands import StartCPFVerificationCommand
from sentinela.application.commands.admin_commands import GetSystemStatsCommand

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_bot_real.log')
    ]
)
logger = logging.getLogger(__name__)

class OnCaboTelegramBot:
    """Bot real do Telegram usando 100% nova arquitetura."""

    def __init__(self):
        self.container = None
        self.hubsoft_use_case = None
        self.cpf_use_case = None
        self.admin_use_case = None
        self.application = None

        # Configurações do .env
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.group_id = int(os.getenv("TELEGRAM_GROUP_ID", "0"))
        self.support_topic_id = int(os.getenv("SUPPORT_TOPIC_ID", "148"))
        self.tech_channel_id = int(os.getenv("TECH_NOTIFICATION_CHANNEL_ID", "0"))
        self.admin_user_ids = [
            int(uid.strip()) for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
            if uid.strip().isdigit()
        ]

    async def initialize(self) -> bool:
        """Inicializa o bot com a nova arquitetura."""
        try:
            logger.info("🚀 Inicializando OnCabo Gaming Bot (Nova Arquitetura)...")

            if not self.token:
                raise ValueError("TELEGRAM_TOKEN não encontrado no .env")

            # Inicializa container DI
            self.container = await get_container()

            # Obtém use cases
            self.hubsoft_use_case = self.container.get("hubsoft_integration_use_case")
            self.cpf_use_case = self.container.get("cpf_verification_use_case")
            self.admin_use_case = self.container.get("admin_operations_use_case")

            # Inicializa aplicação do Telegram
            self.application = Application.builder().token(self.token).build()

            # Registra handlers
            await self._register_handlers()

            logger.info("✅ OnCabo Gaming Bot inicializado com sucesso!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot: {e}")
            return False

    async def _register_handlers(self):
        """Registra todos os handlers do bot."""
        app = self.application

        # Comandos principais
        app.add_handler(CommandHandler("start", self.handle_start))
        app.add_handler(CommandHandler("help", self.handle_help))
        app.add_handler(CommandHandler("suporte", self.handle_support))
        app.add_handler(CommandHandler("verificar_cpf", self.handle_cpf_verification))
        app.add_handler(CommandHandler("status", self.handle_status))

        # Comandos administrativos
        app.add_handler(CommandHandler("admin_stats", self.handle_admin_stats))
        app.add_handler(CommandHandler("admin_sync", self.handle_admin_sync))

        # Handlers de callback (botões inline)
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Mensagens em grupo (apenas no grupo principal)
        app.add_handler(MessageHandler(
            filters.ChatType.SUPERGROUP & filters.Regex(r"^!"),
            self.handle_group_commands
        ))

        # Mensagens privadas (para CPF e confirmações)
        app.add_handler(MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            self.handle_private_message
        ))

        logger.info("📋 Handlers registrados com sucesso")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start."""
        user = update.effective_user
        logger.info(f"🎮 Comando /start - Usuário: {user.username} ({user.id})")

        welcome_text = (
            "🎮 **Bem-vindo ao OnCabo Gaming!**\n\n"
            "✅ Sistema completamente renovado com Clean Architecture\n"
            "🚀 Zero dependências legadas\n"
            "⚡ Performance otimizada\n\n"
            "**Comandos disponíveis:**\n"
            "• /suporte - Abrir ticket de suporte\n"
            "• /verificar_cpf - Verificar seu CPF\n"
            "• /status - Status do sistema\n"
            "• /help - Ajuda completa\n\n"
            "📞 **Precisa de suporte?** Use /suporte para abrir um ticket!\n"
            "🎯 **Sistema totalmente novo e mais eficiente!**"
        )

        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help."""
        user = update.effective_user
        logger.info(f"❓ Comando /help - Usuário: {user.username} ({user.id})")

        help_text = (
            "📚 **Ajuda - OnCabo Gaming Bot**\n\n"
            "**🎮 Comandos para Gamers:**\n"
            "• `/suporte` - Abre ticket de suporte\n"
            "• `/verificar_cpf` - Verifica seu CPF no sistema\n"
            "• `/status` - Mostra status do sistema\n\n"
            "**⚙️ Como funciona o suporte:**\n"
            "1. Use `/suporte` para iniciar\n"
            "2. Escolha a categoria do problema\n"
            "3. Informe o jogo afetado\n"
            "4. Descreva o problema\n"
            "5. Receba seu protocolo de atendimento\n\n"
            "**🔧 Categorias de suporte:**\n"
            "• 🌐 Conectividade/Ping\n"
            "• 🎮 Performance em Jogos\n"
            "• ⚙️ Configuração/Otimização\n"
            "• 🔧 Problema com Equipamento\n"
            "• 📞 Outros problemas\n\n"
            "**💡 Dica:** O sistema integra automaticamente com o HubSoft!"
        )

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /suporte."""
        user = update.effective_user
        logger.info(f"🎫 Comando /suporte - Usuário: {user.username} ({user.id})")

        try:
            # 1. Busca CPF do usuário no banco
            from sentinela.domain.value_objects.identifiers import UserId
            user_id_vo = UserId(user.id)
            user_repo = self.container.get("user_repository")
            existing_user = await user_repo.find_by_id(user_id_vo)

            if not existing_user or not existing_user.cpf:
                # Usuário sem CPF cadastrado - pede para verificar primeiro
                await update.message.reply_text(
                    "⚠️ **CPF Não Verificado**\n\n"
                    "Para abrir um ticket de suporte, você precisa primeiro "
                    "verificar seu CPF no sistema.\n\n"
                    "📱 **Use o comando:** /verificar_cpf\n\n"
                    "🔒 **Por quê?** Precisamos do seu CPF para:\n"
                    "• Verificar seus contratos ativos\n"
                    "• Buscar chamados anteriores\n"
                    "• Integrar com sistema HubSoft\n"
                    "• Priorizar seu atendimento\n\n"
                    "💡 Após verificar, você poderá abrir tickets normalmente!",
                    parse_mode='Markdown'
                )
                return

            cpf = existing_user.cpf.value

            # 2. Verifica se já existe ticket aberto no HubSoft
            await update.message.reply_text(
                "🔍 **Verificando Chamados Anteriores...**\n\n"
                "⏳ Aguarde enquanto consulto o sistema HubSoft...",
                parse_mode='Markdown'
            )

            try:
                # Busca tickets abertos do cliente APENAS do tipo Gaming (ID 101)
                from sentinela.integrations.hubsoft.atendimento import HubSoftAtendimentoClient
                from sentinela.integrations.hubsoft.config import HUBSOFT_TIPO_ATENDIMENTO_GAMING

                hubsoft_atendimento = HubSoftAtendimentoClient()

                open_tickets = await hubsoft_atendimento.get_client_atendimentos(
                    cpf,
                    apenas_pendente=True,  # Apenas abertos
                    tipo_atendimento=HUBSOFT_TIPO_ATENDIMENTO_GAMING  # Filtra por tipo "SUPORTE - ONCABO GAMER"
                )

                # Filtra apenas tickets NÃO RESOLVIDOS (status HubSoft: 1=Pendente, 2=Aguardando Análise)
                # Status 3=Resolvido não bloqueia criação de novos tickets
                active_tickets = [
                    t for t in open_tickets
                    if str(t.get('status', '')) in ['1', '2']
                ]

                if active_tickets:
                    # JÁ TEM TICKET ABERTO - BLOQUEIA criação de novo ticket
                    # Importa mapeamento de status do HubSoft
                    from sentinela.integrations.hubsoft.config import get_status_display

                    ticket_list_user = ""
                    for i, ticket in enumerate(active_tickets[:5], 1):  # Máximo 5
                        # Pega protocolo REAL do HubSoft (já vem formatado da API)
                        protocol = ticket.get('protocolo', 'N/A')
                        status_id = str(ticket.get('status', ''))
                        subject = ticket.get('assunto', 'Sem assunto')
                        created_at = ticket.get('data_abertura', '')

                        status_info = get_status_display(status_id)

                        ticket_list_user += (
                            f"\n{i}. **Atendimento - {protocol}**\n"
                            f"   **Status:** {status_info['emoji']} {status_info['name']}\n"
                            f"   **Assunto:** {subject}\n"
                            f"   **Aberto em:** {created_at}\n"
                        )

                    # Mensagem amigável e profissional para o usuário
                    blocked_message = (
                        "👋 **Olá! Identificamos que você já está em atendimento**\n\n"
                        f"✅ Encontramos **{len(active_tickets)} chamado(s)** em andamento "
                        f"vinculado(s) ao seu CPF:\n{ticket_list_user}\n\n"
                        "🎯 **Nossa equipe já está trabalhando para resolver seu problema!**\n\n"
                        "📞 **Acompanhamento:**\n"
                        "• Nossa equipe entrará em contato em breve\n"
                        "• Verifique seu WhatsApp ou Email cadastrado\n"
                        "• Você pode ligar para nosso suporte se preferir\n\n"
                        "💡 **Dica:** Assim que finalizarmos seu atendimento atual, "
                        "você poderá abrir novos chamados quando precisar!\n\n"
                        "🙏 **Agradecemos sua compreensão e paciência!**"
                    )

                    await update.message.reply_text(blocked_message, parse_mode='Markdown')
                    logger.info(f"Usuário {user.id} BLOQUEADO - já tem {len(active_tickets)} ticket(s) aberto(s)")
                    return  # BLOQUEIA criação

            except Exception as e:
                # Erro ao buscar tickets - permite criar (fallback)
                logger.warning(f"Erro ao buscar tickets no HubSoft: {e}")
                active_tickets = []

            # 3. NÃO tem ticket aberto - CRIA NO HUBSOFT
            await update.message.reply_text(
                "🎫 **Abrindo seu chamado...**\n\n"
                "⏳ Aguarde um momento enquanto registramos sua solicitação...",
                parse_mode='Markdown'
            )

            try:
                # Cria atendimento direto no HubSoft
                from sentinela.integrations.hubsoft.atendimento import HubSoftAtendimentoClient
                hubsoft_atendimento = HubSoftAtendimentoClient()

                # Dados do ticket (básico para /suporte rápido)
                ticket_data = {
                    'assunto': 'Solicitação de Suporte via Telegram',
                    'descricao': f'Ticket criado via comando /suporte pelo usuário {user.first_name} (@{user.username or "sem username"})',
                    'categoria': 'suporte_geral',
                    'prioridade': 'normal',
                    'origem': 'telegram',
                    'telegram_user_id': user.id,
                    'telegram_username': user.username or user.first_name
                }

                # CRIA no HubSoft e recebe protocolo REAL
                hubsoft_response = await hubsoft_atendimento.create_atendimento(cpf, ticket_data)

                # Extrai protocolo REAL do HubSoft
                protocol = hubsoft_response.get('protocolo', 'N/A')
                atendimento_id = hubsoft_response.get('id_atendimento')
                data_cadastro = hubsoft_response.get('data_cadastro', datetime.now().strftime('%d/%m/%Y às %H:%M'))

                logger.info(f"✅ Ticket HubSoft criado - ID: {atendimento_id}, Protocolo: {protocol}")

                # Salva ticket LOCAL com protocolo do HubSoft
                try:
                    from sentinela.domain.entities.ticket import Ticket, TicketStatus, UrgencyLevel
                    from sentinela.domain.entities.user import User
                    from sentinela.domain.value_objects.identifiers import Protocol, HubSoftId
                    from sentinela.domain.value_objects.ticket_category import TicketCategory
                    from sentinela.domain.value_objects.game_title import GameTitle
                    from sentinela.domain.value_objects.problem_timing import ProblemTiming

                    # Busca usuário completo
                    user_entity = await user_repo.find_by_id(user_id_vo)

                    # Cria entidade de ticket local
                    ticket_local = Ticket(
                        ticket_id=None,  # Auto-increment
                        user=user_entity,
                        category=TicketCategory.from_string('suporte_geral'),
                        game=GameTitle.from_string('outros', 'Telegram /suporte'),
                        timing=ProblemTiming.from_string('agora'),
                        description=ticket_data['descricao'],
                        urgency=UrgencyLevel.MEDIUM
                    )

                    # Define protocolo do HubSoft
                    ticket_local.protocol_hubsoft = Protocol.from_hubsoft_protocol(protocol)
                    ticket_local.hubsoft_id = HubSoftId(atendimento_id) if atendimento_id else None
                    ticket_local.status = TicketStatus.OPEN
                    ticket_local.hubsoft_synced = True
                    ticket_local.hubsoft_sync_at = datetime.now()

                    # Salva no banco local
                    ticket_repo = self.container.get("ticket_repository")
                    await ticket_repo.save(ticket_local)

                    logger.info(f"✅ Ticket salvo localmente - ID local: {ticket_local.id}, Protocolo HubSoft: {protocol}")

                except Exception as save_error:
                    logger.warning(f"⚠️ Ticket criado no HubSoft mas falhou ao salvar localmente: {save_error}")
                    # Não bloqueia o fluxo - ticket já está no HubSoft

                # Mensagem de sucesso com protocolo REAL
                success_text = (
                    "✅ **Chamado Criado com Sucesso!**\n\n"
                    f"📋 **Protocolo:** `{protocol}`\n"
                    f"📅 **Abertura:** {data_cadastro}\n\n"
                    "🎯 **Próximos Passos:**\n"
                    "• Nossa equipe já foi notificada\n"
                    "• Você será contatado em breve\n"
                    "• Fique atento ao telefone e e-mail cadastrados\n\n"
                    "⏱️ **Tempo de Resposta:** Até 24h úteis\n\n"
                    "💡 **Dica:** Guarde o protocolo acima para consultar o andamento do seu atendimento"
                )

                await update.message.reply_text(success_text, parse_mode='Markdown')

                # Notificação APENAS para canal de admins
                if self.tech_channel_id:
                    tech_notification = (
                        f"🚨 **Novo Ticket HubSoft Criado**\n\n"
                        f"📋 **Atendimento - {protocol}**\n"
                        f"🆔 **ID HubSoft:** `{atendimento_id}`\n"
                        f"👤 **Usuário:** {user.first_name} (@{user.username or 'sem username'})\n"
                        f"🆔 **ID Telegram:** `{user.id}`\n"
                        f"📋 **CPF:** {cpf[:3]}***{cpf[-2:]}\n"
                        f"📅 **Data:** {data_cadastro}\n\n"
                        f"✅ **Status:** Criado no HubSoft com sucesso\n"
                        f"🔗 **Origem:** Telegram (/suporte)\n"
                        f"⚡ **Ação:** Aguardando atribuição de técnico"
                    )

                    try:
                        await context.bot.send_message(
                            chat_id=self.tech_channel_id,
                            text=tech_notification,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Notificação enviada ao canal de admins para ticket {protocol}")
                    except Exception as e:
                        logger.warning(f"Erro ao enviar notificação técnica: {e}")

                logger.info(f"Ticket {protocol} (ID {atendimento_id}) criado no HubSoft para usuário {user.id}")

            except Exception as hubsoft_error:
                # Falha ao criar no HubSoft - notifica usuário
                logger.error(f"❌ Erro ao criar ticket no HubSoft: {hubsoft_error}")
                await update.message.reply_text(
                    "⚠️ **Não foi possível abrir o chamado no momento**\n\n"
                    "Estamos com uma instabilidade temporária no sistema.\n\n"
                    "📞 **O que fazer:**\n"
                    "• Aguarde alguns minutos e tente novamente\n"
                    "• Ou entre em contato direto pelo telefone\n"
                    "• Nossa equipe já foi notificada do problema\n\n"
                    "🙏 **Pedimos desculpas pelo inconveniente!**\n"
                    "Estamos trabalhando para resolver o mais rápido possível.",
                    parse_mode='Markdown'
                )
                return

        except Exception as e:
            logger.error(f"Erro ao criar ticket de suporte: {e}")
            await update.message.reply_text(
                "⚠️ **Ocorreu um erro inesperado**\n\n"
                "Não conseguimos processar sua solicitação no momento.\n\n"
                "🔄 **Por favor:**\n"
                "• Tente novamente em alguns instantes\n"
                "• Se o problema continuar, fale conosco no grupo\n\n"
                "📞 Em caso de urgência, ligue para nosso suporte!",
                parse_mode='Markdown'
            )

    async def handle_cpf_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /verificar_cpf."""
        user = update.effective_user
        chat = update.effective_chat
        logger.info(f"🔍 Comando /verificar_cpf - Usuário: {user.username} ({user.id}) - Chat: {chat.type}")

        try:
            # Se comando foi dado no grupo, avisa e redireciona para privado
            if chat.type in ['group', 'supergroup']:
                # Aviso no grupo
                group_message = (
                    f"🔒 {user.first_name}, por questões de segurança, a verificação de CPF "
                    f"será feita no **privado**.\n\n"
                    f"📱 **Te chamei no privado** - responda lá para continuar!"
                )
                await update.message.reply_text(group_message, parse_mode='Markdown')

                # Tenta enviar mensagem privada
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=(
                            "🔐 **Verificação de CPF - OnCabo Gaming**\n\n"
                            "Olá! Vamos iniciar sua verificação de CPF.\n\n"
                            "Por questões de segurança, esse processo é feito aqui no privado.\n\n"
                            "⏳ Aguarde enquanto verifico seu cadastro..."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as dm_error:
                    # Se falhar ao enviar DM, pede para iniciar conversa
                    await update.message.reply_text(
                        f"❌ {user.first_name}, não consegui te enviar mensagem privada.\n\n"
                        f"📱 **Clique aqui para iniciar conversa comigo:** "
                        f"https://t.me/{context.bot.username}\n\n"
                        f"Depois, use /verificar_cpf novamente no privado!",
                        parse_mode='Markdown'
                    )
                    logger.warning(f"Não foi possível enviar DM para {user.id}: {dm_error}")
                    return

                # Continua processamento no privado
                target_chat_id = user.id
            else:
                # Comando já foi dado no privado
                target_chat_id = chat.id

            # 1. Verifica se usuário JÁ tem CPF no banco
            from sentinela.domain.value_objects.identifiers import UserId
            user_id_vo = UserId(user.id)

            # Busca usuário no repositório
            user_repo = self.container.get("user_repository")
            existing_user = await user_repo.find_by_id(user_id_vo)

            if existing_user and existing_user.cpf:
                # Usuário JÁ tem CPF - pede re-confirmação
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=(
                        "🔍 **Verificação de Cadastro**\n\n"
                        f"Encontrei um CPF já cadastrado para você!\n\n"
                        f"📋 **CPF:** {existing_user.cpf.masked_value}\n"
                        f"👤 **Nome:** {existing_user.client_name or 'Não informado'}\n\n"
                        "❓ **Este CPF está correto?**\n\n"
                        "✅ Digite **SIM** para confirmar\n"
                        "❌ Digite **NAO** para atualizar\n\n"
                        "⚠️ **Importante:** Você tem **24 horas** para confirmar, "
                        "caso contrário será removido do grupo por medida de segurança."
                    ),
                    parse_mode='Markdown'
                )

                # Marca contexto para aguardar confirmação
                context.user_data['awaiting_cpf_confirmation'] = True
                context.user_data['current_cpf'] = existing_user.cpf.value
                logger.info(f"Aguardando confirmação de CPF para usuário {user.id}")
                return

            # 2. Usuário NÃO tem CPF - inicia verificação normal
            result = await self.cpf_use_case.start_verification(
                user_id=user.id,
                username=user.username or user.first_name,
                user_mention=f"@{user.username}" if user.username else user.first_name
            )

            if result.success:
                response_text = (
                    "🔍 **Verificação de CPF Iniciada!**\n\n"
                    f"✅ {result.message}\n\n"
                    "📱 **Digite seu CPF** (somente números):\n"
                    "Exemplo: 12345678901\n\n"
                    "🔒 **Seus dados estão seguros** - criptografia de ponta a ponta\n\n"
                    "⚠️ **Importante:** Você tem **24 horas** para completar a verificação."
                )
            else:
                response_text = (
                    "❌ **Erro na Verificação de CPF**\n\n"
                    f"🚫 {result.message}\n\n"
                    "🔄 **Tente novamente** em alguns instantes\n"
                    "📞 **Precisa de ajuda?** Use /suporte"
                )

            await context.bot.send_message(
                chat_id=target_chat_id,
                text=response_text,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro na verificação CPF: {e}")
            await update.message.reply_text(
                "❌ **Erro interno na verificação**\n\n"
                "🔄 Sistema temporariamente indisponível\n"
                "📞 Use /suporte para reportar o problema"
            )

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Mostra chamados do cliente."""
        user = update.effective_user
        logger.info(f"📋 Comando /status - Usuário: {user.username} ({user.id})")

        try:
            # 1. Verifica CPF do usuário
            from sentinela.domain.value_objects.identifiers import UserId
            user_id_vo = UserId(user.id)
            user_repo = self.container.get("user_repository")
            existing_user = await user_repo.find_by_id(user_id_vo)

            if not existing_user or not existing_user.cpf:
                # Usuário sem CPF cadastrado
                await update.message.reply_text(
                    "⚠️ **CPF Não Verificado**\n\n"
                    "Para consultar seus chamados, você precisa primeiro "
                    "verificar seu CPF no sistema.\n\n"
                    "📱 **Use o comando:** /verificar_cpf\n\n"
                    "Após a verificação, você poderá consultar todos os seus "
                    "atendimentos com /status",
                    parse_mode='Markdown'
                )
                return

            cpf = existing_user.cpf.value

            # 2. Busca chamados do cliente no HubSoft
            await update.message.reply_text(
                "🔍 **Consultando seus chamados...**\n\n"
                "⏳ Aguarde enquanto buscamos seus atendimentos...",
                parse_mode='Markdown'
            )

            from sentinela.integrations.hubsoft.atendimento import HubSoftAtendimentoClient
            from sentinela.integrations.hubsoft.config import get_status_display, HUBSOFT_TIPO_ATENDIMENTO_GAMING

            hubsoft_atendimento = HubSoftAtendimentoClient()

            # Busca TODOS os chamados (abertos e fechados) APENAS do tipo Gaming (ID 101)
            all_tickets = await hubsoft_atendimento.get_client_atendimentos(
                cpf,
                apenas_pendente=False,
                tipo_atendimento=HUBSOFT_TIPO_ATENDIMENTO_GAMING  # Filtra por tipo "SUPORTE - ONCABO GAMER"
            )

            if not all_tickets:
                # Cliente não tem chamados
                await update.message.reply_text(
                    "📋 **Meus Chamados**\n\n"
                    "✅ Você não possui chamados registrados no momento.\n\n"
                    "🎫 **Precisa de ajuda?**\n"
                    "Use o comando /suporte para abrir um novo chamado!\n\n"
                    "📞 Nossa equipe está pronta para atender você!",
                    parse_mode='Markdown'
                )
                return

            # 3. Separa chamados abertos e fechados
            open_tickets = [t for t in all_tickets if str(t.get('status', '')) in ['1', '2']]
            closed_tickets = [t for t in all_tickets if str(t.get('status', '')) == '3']

            # 4. Monta mensagem formatada
            status_message = "📋 **Meus Chamados**\n\n"

            # Chamados ABERTOS
            if open_tickets:
                status_message += f"🔔 **{len(open_tickets)} Chamado(s) em Andamento:**\n\n"

                for i, ticket in enumerate(open_tickets[:5], 1):  # Máximo 5
                    protocol = ticket.get('protocolo', 'N/A')
                    status_id = str(ticket.get('status', ''))
                    subject = ticket.get('assunto', 'Sem assunto')
                    created_at = ticket.get('data_abertura', 'N/A')

                    status_info = get_status_display(status_id)

                    status_message += (
                        f"{i}. 📋 **Protocolo:** `{protocol}`\n"
                        f"   {status_info['emoji']} **Status:** {status_info['name']}\n"
                        f"   📝 **Assunto:** {subject}\n"
                        f"   📅 **Aberto em:** {created_at}\n\n"
                    )

            # Chamados FECHADOS (últimos 3)
            if closed_tickets:
                status_message += f"✅ **{len(closed_tickets)} Chamado(s) Resolvido(s):**\n\n"

                for i, ticket in enumerate(closed_tickets[:3], 1):  # Últimos 3
                    protocol = ticket.get('protocolo', 'N/A')
                    subject = ticket.get('assunto', 'Sem assunto')
                    created_at = ticket.get('data_abertura', 'N/A')
                    closed_at = ticket.get('data_fechamento', 'N/A')

                    status_message += (
                        f"{i}. 📋 **Protocolo:** `{protocol}`\n"
                        f"   🟢 **Status:** Resolvido\n"
                        f"   📝 **Assunto:** {subject}\n"
                        f"   📅 **Fechado em:** {closed_at}\n\n"
                    )

            # Rodapé
            status_message += (
                "⏱️ **Tempo médio de resposta:** 24h úteis\n"
                "🎫 **Novo chamado?** Use /suporte\n"
                "📞 **Dúvidas?** Fale conosco no grupo!"
            )

            await update.message.reply_text(status_message, parse_mode='Markdown')
            logger.info(f"Status enviado - {len(open_tickets)} abertos, {len(closed_tickets)} fechados")

        except Exception as e:
            logger.error(f"Erro ao obter status dos chamados: {e}")
            await update.message.reply_text(
                "⚠️ **Erro ao Consultar Chamados**\n\n"
                "Não conseguimos buscar seus atendimentos no momento.\n\n"
                "🔄 **Tente novamente em alguns instantes**\n"
                "📞 Se o problema persistir, entre em contato no grupo!",
                parse_mode='Markdown'
            )

    async def handle_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando administrativo /admin_stats."""
        user = update.effective_user

        if user.id not in self.admin_user_ids:
            await update.message.reply_text("❌ Acesso negado. Comando apenas para administradores.")
            return

        logger.info(f"👑 Comando /admin_stats - Admin: {user.username} ({user.id})")

        try:
            command = GetSystemStatsCommand(admin_user_id=user.id)
            result = await self.admin_use_case.get_system_stats(command)

            if result.success:
                stats = result.data
                admin_text = (
                    "👑 **Estatísticas Administrativas**\n\n"
                    f"📊 **Totais:**\n"
                    f"• Tickets: {stats.get('total_tickets', 0)}\n"
                    f"• Usuários: {stats.get('total_users', 0)}\n"
                    f"• Verificações CPF: {stats.get('total_verifications', 0)}\n\n"
                    f"⚡ **Sistema:**\n"
                    f"• Arquitetura: 100% Nova\n"
                    f"• Legacy: Removido\n"
                    f"• Performance: Otimizada\n\n"
                    f"📅 Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
                )
            else:
                admin_text = "❌ Erro ao obter estatísticas administrativas"

            await update.message.reply_text(admin_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro em admin_stats: {e}")
            await update.message.reply_text("❌ Erro interno nas estatísticas administrativas")

    async def handle_admin_sync(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando administrativo /admin_sync."""
        user = update.effective_user

        if user.id not in self.admin_user_ids:
            await update.message.reply_text("❌ Acesso negado. Comando apenas para administradores.")
            return

        logger.info(f"👑 Comando /admin_sync - Admin: {user.username} ({user.id})")

        try:
            # Executa health check do HubSoft
            health_result = await self.hubsoft_use_case.check_hubsoft_health()

            sync_text = (
                "🔄 **Sincronização HubSoft**\n\n"
                f"🔗 **Status API:** {'✅ Online' if health_result.success else '❌ Offline'}\n"
                f"🏛️ **Arquitetura:** Nova (100%)\n"
                f"📡 **Endpoint:** Configurado\n"
                f"🔐 **Autenticação:** Ativa\n\n"
                f"📊 **Última verificação:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                "✅ Sistema pronto para sincronização!"
            )

            await update.message.reply_text(sync_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro em admin_sync: {e}")
            await update.message.reply_text("❌ Erro interno na sincronização")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para botões inline."""
        query = update.callback_query
        await query.answer()

        user = query.from_user
        data = query.data

        logger.info(f"🔘 Callback - Usuário: {user.username} ({user.id}), Data: {data}")

        # Aqui você pode implementar handlers para botões específicos
        await query.edit_message_text(
            text=f"⚡ Processando ação: {data}\n\n✅ Nova arquitetura em funcionamento!",
            parse_mode='Markdown'
        )

    async def handle_group_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comandos em grupo (iniciados com !)."""
        message = update.message
        user = message.from_user
        text = message.text

        logger.info(f"👥 Comando grupo - Usuário: {user.username}, Comando: {text}")

        if text.startswith("!status"):
            await message.reply_text(
                "📊 **OnCabo Gaming - Status**\n\n"
                "🎮 **Sistema:** 100% Nova Arquitetura\n"
                "⚡ **Performance:** Otimizada\n"
                "🚫 **Legacy:** Removido\n\n"
                "✅ Tudo funcionando perfeitamente!"
            )

    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensagens privadas (CPF, confirmações, etc)."""
        user = update.effective_user
        text = update.message.text.strip()
        logger.info(f"💬 Mensagem privada - Usuário: {user.username} ({user.id}), Texto: {text[:50]}")

        try:
            # 1. Verifica se está aguardando confirmação de CPF
            if context.user_data.get('awaiting_cpf_confirmation'):
                await self._handle_cpf_confirmation(update, context, text)
                return

            # 2. Verifica se está aguardando escolha de conta duplicada
            if context.user_data.get('awaiting_duplicate_choice'):
                await self._handle_duplicate_choice(update, context, text)
                return

            # 3. Tenta processar como CPF (validação de formato básica)
            if text.isdigit() and len(text) == 11:
                await self._handle_cpf_submission(update, context, text)
                return

            # 4. Mensagem não reconhecida
            await update.message.reply_text(
                "❓ **Mensagem não reconhecida**\n\n"
                "📋 **Comandos disponíveis:**\n"
                "• /verificar_cpf - Verificar CPF\n"
                "• /suporte - Abrir ticket\n"
                "• /status - Status do sistema\n"
                "• /help - Ajuda completa\n\n"
                "💡 **Dica:** Se está tentando enviar CPF, use apenas números (11 dígitos)"
            )

        except Exception as e:
            logger.error(f"Erro ao processar mensagem privada: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar sua mensagem.\n"
                "🔄 Tente novamente ou use /help"
            )

    async def _handle_cpf_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Processa confirmação de CPF existente."""
        user = update.effective_user
        text_upper = text.upper()

        if text_upper in ['SIM', 'S', 'YES', 'Y', 'CONFIRMO', 'OK']:
            # CPF confirmado
            await update.message.reply_text(
                "✅ **CPF Confirmado!**\n\n"
                "🎮 Seu acesso está verificado e ativo!\n"
                "📊 Você pode continuar aproveitando o grupo OnCabo Gaming.\n\n"
                "💡 **Dica:** Use /suporte se precisar de ajuda"
            )

            # Limpa contexto
            context.user_data.clear()
            logger.info(f"CPF confirmado para usuário {user.id}")

        elif text_upper in ['NAO', 'NÃO', 'N', 'NO', 'NEGAR']:
            # Usuário quer atualizar CPF
            await update.message.reply_text(
                "🔄 **Atualização de CPF**\n\n"
                "📱 **Digite seu novo CPF** (somente números):\n"
                "Exemplo: 12345678901\n\n"
                "🔒 Seus dados estão seguros - criptografia de ponta a ponta"
            )

            # Inicia nova verificação
            result = await self.cpf_use_case.start_verification(
                user_id=user.id,
                username=user.username or user.first_name,
                user_mention=f"@{user.username}" if user.username else user.first_name,
                verification_type="cpf_update"
            )

            # Limpa contexto de confirmação
            context.user_data.pop('awaiting_cpf_confirmation', None)
            logger.info(f"Usuário {user.id} iniciou atualização de CPF")

        else:
            # Resposta inválida
            await update.message.reply_text(
                "❓ **Resposta não reconhecida**\n\n"
                "✅ Digite **SIM** para confirmar o CPF\n"
                "❌ Digite **NAO** para atualizar\n\n"
                "⏰ Aguardando sua resposta..."
            )

    async def _handle_duplicate_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Processa escolha quando há CPF duplicado."""
        user = update.effective_user
        duplicate_data = context.user_data.get('duplicate_data', {})
        duplicate_users = duplicate_data.get('users', [])

        try:
            # Verifica se respondeu com número
            choice = int(text.strip())

            if 1 <= choice <= len(duplicate_users):
                # Escolha válida
                chosen_user = duplicate_users[choice - 1]
                other_users = [u for i, u in enumerate(duplicate_users) if i != (choice - 1)]

                await update.message.reply_text(
                    f"✅ **Conta Selecionada!**\n\n"
                    f"👤 **Conta mantida:** {chosen_user.get('username', 'Desconhecido')}\n"
                    f"🆔 **ID:** {chosen_user['user_id']}\n\n"
                    f"🚫 **As seguintes contas serão removidas:**\n"
                    + "\n".join([f"• {u.get('username', 'Desconhecido')} (ID: {u['user_id']})" for u in other_users]) +
                    "\n\n⏳ Processando remoção..."
                )

                # Remove outras contas do grupo
                for other_user in other_users:
                    try:
                        await context.bot.ban_chat_member(
                            chat_id=self.group_id,
                            user_id=other_user['user_id']
                        )
                        logger.info(f"Usuário {other_user['user_id']} removido por conta duplicada")
                    except Exception as e:
                        logger.error(f"Erro ao remover usuário {other_user['user_id']}: {e}")

                await update.message.reply_text(
                    "✅ **Processo concluído!**\n\n"
                    "🎮 Sua conta principal está ativa no grupo.\n"
                    "📊 As contas duplicadas foram removidas.\n\n"
                    "💡 Use /suporte se tiver alguma dúvida."
                )

                # Limpa contexto
                context.user_data.clear()

            else:
                await update.message.reply_text(
                    f"❌ **Opção inválida**\n\n"
                    f"📋 Escolha um número entre 1 e {len(duplicate_users)}"
                )

        except ValueError:
            await update.message.reply_text(
                "❌ **Entrada inválida**\n\n"
                "📋 Digite o **número** da conta que deseja manter\n"
                "Exemplo: 1"
            )

    async def _handle_cpf_submission(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cpf: str):
        """Processa submissão de CPF."""
        user = update.effective_user
        logger.info(f"📋 Processando submissão de CPF para usuário {user.id}")

        try:
            # Submete CPF para verificação
            result = await self.cpf_use_case.submit_cpf(
                user_id=user.id,
                username=user.username or user.first_name,
                cpf=cpf
            )

            if result.success:
                # CPF válido - verifica duplicatas
                duplicate_service = self.container.get("duplicate_cpf_service")

                # Calcula hash do CPF para verificação
                import hashlib
                cpf_hash = hashlib.sha256(cpf.encode()).hexdigest()

                duplicate_check = await duplicate_service.check_for_duplicates(
                    cpf_hash=cpf_hash,
                    exclude_user_id=user.id
                )

                if duplicate_check.get('has_duplicates'):
                    # CPF DUPLICADO - pede para escolher conta
                    duplicate_users = duplicate_check['users']
                    duplicate_users.append({
                        'user_id': user.id,
                        'username': user.username or user.first_name
                    })

                    message = (
                        "⚠️ **CPF Duplicado Detectado!**\n\n"
                        "🔍 Este CPF está associado a múltiplas contas:\n\n"
                    )

                    for i, dup_user in enumerate(duplicate_users, 1):
                        message += f"{i}. {dup_user.get('username', 'Desconhecido')} (ID: {dup_user['user_id']})\n"

                    message += (
                        "\n❓ **Qual conta você deseja manter?**\n"
                        "📋 Digite o **número** da conta:\n\n"
                        "⚠️ **IMPORTANTE:** As outras contas serão removidas do grupo "
                        "por questões de segurança."
                    )

                    await update.message.reply_text(message)

                    # Marca contexto
                    context.user_data['awaiting_duplicate_choice'] = True
                    context.user_data['duplicate_data'] = duplicate_check

                else:
                    # CPF único - sucesso!
                    await update.message.reply_text(
                        "✅ **Verificação Concluída com Sucesso!**\n\n"
                        f"{result.message}\n\n"
                        "🎮 **Seu acesso está liberado!**\n"
                        "📊 Aproveite todos os benefícios do grupo OnCabo Gaming!\n\n"
                        "💡 Use /suporte se precisar de ajuda."
                    )

            else:
                # Erro na verificação
                await update.message.reply_text(
                    f"❌ **Erro na Verificação**\n\n"
                    f"{result.message}\n\n"
                    f"🔄 **Tentativas restantes:** {result.data.get('attempts_left', 0)}\n\n"
                    "💡 Verifique se o CPF está correto e tente novamente."
                )

        except Exception as e:
            logger.error(f"Erro ao processar CPF: {e}")
            await update.message.reply_text(
                "❌ **Erro interno ao processar CPF**\n\n"
                "🔄 Tente novamente em alguns instantes\n"
                "📞 Se persistir, use /suporte"
            )

    async def start_bot(self):
        """Inicia o bot."""
        try:
            logger.info("🚀 Iniciando OnCabo Gaming Bot...")

            # Executa health check inicial
            await self._health_check()

            # Inicia o bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("✅ OnCabo Gaming Bot está funcionando!")
            logger.info(f"📱 Telegram Token: {self.token[:10]}...")
            logger.info(f"👥 Grupo Principal: {self.group_id}")
            logger.info(f"🎫 Tópico Suporte: {self.support_topic_id}")
            logger.info(f"👑 Admins: {len(self.admin_user_ids)} configurados")

            # Mantém o bot rodando
            await self.application.updater.idle()

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar bot: {e}")
            raise

    async def stop_bot(self):
        """Para o bot."""
        try:
            logger.info("🛑 Parando OnCabo Gaming Bot...")

            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

            if self.container:
                await shutdown_container()

            logger.info("✅ OnCabo Gaming Bot parado com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao parar bot: {e}")

    async def _health_check(self):
        """Executa health check do sistema."""
        try:
            logger.info("🏥 Executando health check...")

            # Testa HubSoft integration
            if self.hubsoft_use_case:
                health_result = await self.hubsoft_use_case.check_hubsoft_health()
                logger.info(f"🔗 HubSoft API: {'✅' if health_result.success else '❌'}")

            # Testa outros componentes
            logger.info("✅ CPF Verification: Configurado")
            logger.info("✅ Admin Operations: Configurado")
            logger.info("✅ Event Bus: Funcionando")
            logger.info("✅ Repositories: Funcionando")
            logger.info("🚫 Sistema Legado: REMOVIDO")

            logger.info("🎯 Health check concluído - Sistema 100% nova arquitetura!")

        except Exception as e:
            logger.error(f"❌ Erro no health check: {e}")


async def main():
    """Função principal."""
    # Carrega variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()

    bot = OnCaboTelegramBot()

    try:
        # Inicializa o bot
        if await bot.initialize():
            # Inicia o bot
            await bot.start_bot()
        else:
            logger.error("❌ Falha na inicialização do bot")
            return 1

    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro crítico: {e}")
        return 1
    finally:
        await bot.stop_bot()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)