"""
Telegram Bot Handler.

Camada de apresentação para integração com Telegram Bot,
utilizando a nova arquitetura com dependency injection.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...infrastructure.config.dependency_injection import get_container
from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
from ...domain.value_objects.identifiers import UserId
from ...domain.entities.cpf_verification import VerificationStatus
from ...core.config import SUPPORT_TOPIC_ID, TELEGRAM_GROUP_ID
from .cpf_verification_handler import CPFVerificationHandler
from .support_form_handler import (
    SupportFormHandler,
    SupportState,
    get_progress_bar
)

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """Handler principal para interações do Telegram Bot."""

    def __init__(self):
        self._container = None
        self._hubsoft_use_case: Optional[HubSoftIntegrationUseCase] = None
        self._cpf_use_case: Optional[CPFVerificationUseCase] = None
        self._welcome_use_case = None  # WelcomeManagementUseCase
        self._cpf_handler: Optional[CPFVerificationHandler] = None
        self._support_handler: Optional[SupportFormHandler] = None
        self._admin_repo = None  # AdminRepository

    async def _ensure_initialized(self) -> None:
        """Garante que o handler está inicializado."""
        if self._container is None:
            self._container = get_container()
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")
            self._cpf_use_case = self._container.get("cpf_verification_use_case")
            self._welcome_use_case = self._container.get("welcome_management_use_case")
            self._cpf_handler = CPFVerificationHandler(self._container)
            self._support_handler = SupportFormHandler(self._container)
            self._admin_repo = self._container.get("admin_repository")

    async def _user_already_interacted(self, user_id: int) -> bool:
        """
        Verifica se usuário já teve alguma interação anterior (passou pelo fluxo).

        Verifica se existe QUALQUER registro de verificação (completa, pendente ou expirada).
        Se existe = usuário já passou pelo fluxo de boas-vindas.

        Args:
            user_id: ID do usuário do Telegram

        Returns:
            bool: True se usuário já interagiu antes, False se é primeira vez
        """
        try:
            await self._ensure_initialized()

            cpf_repo = self._container.get("cpf_verification_repository")
            if not cpf_repo:
                return False

            # Busca QUALQUER verificação (completa ou não)
            verifications = await cpf_repo.find_by_user_id(user_id, limit=1)

            # Se tem alguma verificação = já passou pelo fluxo
            has_interacted = len(verifications) > 0

            if has_interacted:
                logger.debug(f"Usuário {user_id} já interagiu anteriormente")
            else:
                logger.debug(f"Usuário {user_id} é novo (primeira interação)")

            return has_interacted

        except Exception as e:
            logger.error(f"Erro ao verificar histórico do usuário {user_id}: {e}")
            return False

    async def _check_user_verified(self, user_id: int) -> bool:
        """
        Verifica se um usuário está ATIVO no sistema.

        Delega para CPFVerificationHandler.

        Args:
            user_id: ID do usuário do Telegram.

        Returns:
            bool: True se o usuário existe e está ativo, False caso contrário.
        """
        await self._ensure_initialized()
        return await self._cpf_handler.check_user_verified(user_id)

    async def _get_verification_status_message(self, user_id: int) -> dict:
        """
        Retorna mensagem contextualizada baseada no status da verificação.

        Delega para CPFVerificationHandler.

        Returns:
            dict: {
                "is_verified": bool,
                "status": str,
                "message": str
            }
        """
        await self._ensure_initialized()
        return await self._cpf_handler.get_verification_status_message(user_id)

    async def _start_welcome_flow(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Inicia fluxo de boas-vindas e validação de CPF para usuário não verificado.

        Args:
            update: Update do Telegram
            context: Context do bot
        """
        try:
            user = update.effective_user
            if not user:
                return

            from ...core.config import ONCABO_SITE_URL, ONCABO_WHATSAPP_URL

            # Texto de boas-vindas acolhedor (baseado em welcome_message.py)
            welcome_text = (
                f"🎮 <b>Olá, {user.first_name}! Eu sou o OnCabito!</b> 🤖\n\n"
                "Sou o assistente oficial responsável por gerenciar o melhor "
                "grupo de suporte gaming da OnCabo! 🔥\n\n"
                "Nossa comunidade é exclusiva para assinantes do plano "
                "OnCabo Gaming, onde você encontra:\n\n"
                "🎯 Suporte técnico especializado em jogos\n"
                "👥 Outros gamers para jogar em squad\n"
                "🏆 Dicas, torneios e muito mais!\n\n"
                "📋 <b>PARA LIBERAR SEU ACESSO</b>\n\n"
                "Para verificar se você tem um plano ativo e liberar sua "
                "entrada no grupo, preciso validar seu CPF.\n\n"
                "🔒 <b>Fique tranquilo:</b> Seus dados são protegidos e usados "
                "apenas para verificação do seu contrato.\n\n"
                "📝 <b>Por favor, me envie seu CPF</b> (apenas os 11 números):\n\n"
                f"💡 <b>Não é assinante ainda?</b>\n"
                f"🌐 Conheça nossos planos: {ONCABO_SITE_URL or 'oncabo.com.br'}\n"
                f"📞 Fale conosco: {ONCABO_WHATSAPP_URL or 'WhatsApp OnCabo'}"
            )

            # Envia mensagem de boas-vindas
            await update.message.reply_text(
                welcome_text,
                parse_mode='HTML'
            )

            # CRÍTICO: Cria verificação pendente no banco ANTES de pedir CPF
            logger.info(f"Criando verificação pendente para usuário {user.id}")
            verification_result = await self._cpf_use_case.start_verification(
                user_id=user.id,
                username=user.username or user.first_name,
                user_mention=f"<a href='tg://user?id={user.id}'>{user.first_name}</a>",
                verification_type="auto_checkup",
                source_action="auto welcome flow"
            )

            if not verification_result.success:
                logger.error(f"Erro ao criar verificação: {verification_result.message}")
                await update.message.reply_text(
                    "❌ Erro ao iniciar verificação. Tente novamente em alguns instantes.",
                    parse_mode='HTML'
                )
                return

            logger.info(f"Verificação criada: {verification_result.verification_id}")

            # Define estado conversacional aguardando CPF
            context.user_data['waiting_cpf'] = True

            # Agenda um lembrete para 5 minutos (300 segundos) via CPF handler
            self._cpf_handler.schedule_cpf_reminder(context, user.id, delay_seconds=300)

            logger.info(f"Fluxo de boas-vindas iniciado para usuário {user.id}")

        except Exception as e:
            logger.error(f"Erro ao iniciar fluxo de boas-vindas: {e}")
            await update.message.reply_text(
                "❌ Ocorreu um erro inesperado. Tente novamente mais tarde."
            )

    async def handle_start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /start - Apresentação do OnCabito e solicitação de CPF."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            chat = update.effective_chat
            if not user:
                return

            # Verifica se é conversa privada
            if chat.type == 'private':
                # LÓGICA CORRIGIDA: Verifica se o usuário já é um membro verificado e ativo no grupo.
                try:
                    from telegram.error import BadRequest
                    member = await context.bot.get_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user.id)
                    if member and member.status in ['creator', 'administrator', 'member']:
                        logger.info(f"Usuário {user.id} (membro do grupo, status: {member.status}) usou /start.")

                        # Etapa 1: Diferenciar Admin de Usuário Normal
                        if await self._is_admin(user.id):
                            logger.info(f"Usuário {user.id} é admin. Exibindo menu de admin.")
                            keyboard = [
                                [
                                    InlineKeyboardButton("📋 Listar Tickets", callback_data="admin_list_tickets"),
                                    InlineKeyboardButton("📊 Estatísticas", callback_data="admin_stats")
                                ],
                                [
                                    InlineKeyboardButton("🔄 Sync HubSoft", callback_data="admin_sync"),
                                    InlineKeyboardButton("⚙️ Configurações", callback_data="admin_config")
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            message = (
                                f"👋 Olá, {user.first_name}! Como administrador, o que você gostaria de fazer?"
                            )
                            await update.message.reply_text(message, reply_markup=reply_markup)

                        else:
                            logger.info(f"Usuário {user.id} é membro normal. Exibindo opções de suporte.")
                            keyboard = [
                                [
                                    InlineKeyboardButton("➕ Abrir novo chamado", callback_data="start_flow_support"),
                                    InlineKeyboardButton("🔍 Verificar chamado", callback_data="start_flow_status")
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            message = (
                                f"👋 Olá, {user.first_name}! Você já está em nosso grupo de suporte. O que deseja fazer?"
                            )
                            await update.message.reply_text(message, reply_markup=reply_markup)

                        return # Finaliza o fluxo de /start para membros existentes

                except BadRequest:
                    # Erro esperado se o usuário não estiver no grupo. Continua o fluxo normal.
                    logger.debug(f"Usuário {user.id} não é membro do grupo (BadRequest). Continuando com o fluxo de /start.")
                except Exception as e:
                    # Outros erros podem ser de configuração (e.g., bot não é admin).
                    # Loga como erro e avisa o usuário, mas não continua o fluxo para evitar comportamento inesperado.
                    logger.error(f"Erro inesperado ao verificar se usuário {user.id} é membro do grupo. Pode ser um problema de permissão ou configuração. Erro: {e}", exc_info=True)
                    await update.message.reply_text(
                        "🤖 Ops! Tive um problema para verificar suas informações. "
                        "Por favor, tente novamente em alguns instantes ou contate o suporte se o erro persistir."
                    )
                    return

                # Apresentação do OnCabito e solicitação de CPF (FLUXO DE RESET)
                # Esta parte agora é executada para qualquer usuário não-membro, resetando a conversa.
                from ...core.config import ONCABO_SITE_URL, ONCABO_WHATSAPP_URL

                welcome_message = (
                    f"🎮 <b>Olá, {user.first_name}! Eu sou o OnCabito!</b> 🤖\n\n"
                    "Sou o assistente oficial responsável por gerenciar o melhor "
                    "grupo de suporte gaming da OnCabo! 🔥\n\n"
                    "Nossa comunidade é exclusiva para assinantes do plano "
                    "OnCabo Gaming, onde você encontra:\n\n"
                    "🎯 Suporte técnico especializado em jogos\n"
                    "👥 Outros gamers para jogar em squad\n"
                    "🏆 Dicas, torneios e muito mais!\n\n"
                    "📋 <b>PARA LIBERAR SEU ACESSO</b>\n\n"
                    "Para verificar se você tem um plano ativo e liberar sua "
                    "entrada no grupo, preciso validar seu CPF.\n\n"
                    "🆔 <b>Por favor, envie seu CPF (apenas números):</b>\n\n"
                    "Exemplo: <code>12345678900</code>"
                )

                await update.message.reply_text(
                    welcome_message,
                    parse_mode='HTML'
                )

                # Garante que o estado de verificação seja criado ou exista.
                # A lógica de 'reset' é simplesmente ignorar a falha de 'já existe'.
                logger.info(f"Garantindo estado de verificação pendente para usuário {user.id} via /start.")
                verification_result = await self._cpf_use_case.start_verification(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    user_mention=f"<a href='tg://user?id={user.id}'>{user.first_name}</a>",
                    verification_type="auto_checkup",
                    source_action="/start command"
                )

                if not verification_result.success:
                    # Primeiro, trata o caso de limite de tentativas
                    if hasattr(verification_result, 'error_code') and verification_result.error_code == "rate_limited":
                        logger.warning(f"Usuário {user.id} atingiu o limite de tentativas de verificação. Mensagem: {verification_result.message}")
                        await update.message.reply_text(
                            "⚠️ **Limite de Tentativas Atingido**\n\n"
                            "Você realizou muitas tentativas de verificação nas últimas 24 horas. "
                            "Por favor, aguarde e tente novamente amanhã ou entre em contato com o suporte se acreditar que isso é um erro.",
                            parse_mode='Markdown'
                        )
                        return

                    # A única falha que não ignoramos é uma que não seja 'already pending'.
                    if "já existe" not in verification_result.message.lower() and "already pending" not in verification_result.message.lower():
                        logger.error(f"Erro ao criar verificação: {verification_result.message}")
                        await update.message.reply_text(
                            "❌ Erro ao iniciar verificação. Tente novamente em alguns instantes.",
                            parse_mode='HTML'
                        )
                        return
                    else:
                        logger.info(f"Usuário {user.id} já tinha verificação pendente. Continuando fluxo de /start (reset). ")

                # Define estado conversacional aguardando CPF, garantindo que o bot está pronto para o input.
                context.user_data['waiting_cpf'] = True
                logger.info(f"Usuário {user.id} (re)iniciou o fluxo de /start - aguardando CPF.")

                # Agenda um lembrete para 5 minutos (300 segundos) via CPF handler
                self._cpf_handler.schedule_cpf_reminder(context, user.id, delay_seconds=300)

            else:
                # Mensagem para uso em grupo
                message = (
                    f"👋 Olá, {user.first_name}!\n\n"
                    "Para começar, me envie uma mensagem <b>privada</b> clicando "
                    "no meu nome e usando o comando /start.\n\n"
                    "Lá eu vou te ajudar a acessar o grupo! 🎮"
                )
                await update.message.reply_text(
                    message,
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Erro no comando /start: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Ocorreu um erro inesperado. Tente novamente mais tarde."
            )

    async def _check_and_redirect_unverified_group_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verifica se o usuário não é verificado em um grupo e o redireciona para o privado."""
        user = update.effective_user
        is_group = update.effective_chat.id != user.id

        if is_group and not await self._check_user_verified(user.id):
            try:
                # Deleta o comando do grupo para não poluir
                await update.message.delete()

                # Envia instrução no privado
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        "Olá! Para usar os comandos do bot no grupo, você precisa primeiro verificar seu CPF.\n\n"
                        "Vamos fazer isso agora! Por favor, me envie seu CPF (apenas números) aqui no privado."
                    )
                )
                
                # Inicia o fluxo de verificação silenciosamente
                await self._cpf_use_case.start_verification(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    user_mention=user.mention_html,
                    source_action="unverified_group_command"
                )
                context.user_data['waiting_cpf'] = True
                logger.info(f"Usuário não verificado {user.id} tentou usar comando no grupo. Redirecionado para o privado.")
                return False  # Indica que a execução do handler principal deve parar
            except Exception as e:
                logger.error(f"Erro ao redirecionar usuário não verificado: {e}")
                return False # Impede a continuação em caso de erro

        return True # Indica que o usuário está verificado ou no privado, pode continuar

    async def handle_support_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /suporte - Inicia fluxo conversacional."""
        try:
            await self._ensure_initialized()
            user = update.effective_user
            if not user:
                return

            # Guarda de verificação: redireciona se for usuário não verificado no grupo
            if not await self._check_and_redirect_unverified_group_user(update, context):
                return

            # A partir daqui, o usuário ou está no privado ou já é verificado
            chat_id = update.effective_chat.id
            is_group = chat_id != user.id

            # VALIDAÇÃO: Verifica se já tem ticket ativo
            active_result = await self._hubsoft_use_case.get_user_active_tickets(user.id)
            if active_result.success and active_result.data.get('has_active'):
                active_ticket = active_result.data.get('tickets', [])[0]
                protocol = active_ticket.get('protocol') or f"HS-{active_ticket.get('id', 'N/A')}"
                status_display = active_ticket.get('status_display', 'N/A')
                message_text = (
                    f"Olá, {user.mention_markdown()}! 😊\n\n"
                    f"🎮 Vejo que você já tem um atendimento em andamento (Protocolo: `{protocol}`, Status: {status_display}).\n\n"
                    f"Por favor, aguarde a resolução antes de abrir um novo chamado."
                )
                await update.message.reply_text(message_text, parse_mode='Markdown')
                return

            # Se foi enviado no grupo, notifica e sai
            if is_group:
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=int(SUPPORT_TOPIC_ID) if SUPPORT_TOPIC_ID else None,
                    text=f"👋 Olá, {user.mention_markdown()}! Recebi seu pedido de suporte e já estou te chamando no privado para começarmos! 🚀",
                    parse_mode='Markdown'
                )
            
            # Inicia o fluxo de suporte no privado
            await self._support_handler.start_support_flow(user.id)
            state = await self._support_handler._get_support_state(user.id)

            keyboard = [
                [InlineKeyboardButton("🌐 Conectividade/Ping", callback_data="sup_cat_connectivity"),
                 InlineKeyboardButton("⚡ Performance/FPS", callback_data="sup_cat_performance")],
                [InlineKeyboardButton("🎮 Problemas no Jogo", callback_data="sup_cat_game_issues"),
                 InlineKeyboardButton("💻 Configuração", callback_data="sup_cat_configuration")],
                [InlineKeyboardButton("📞 Outros", callback_data="sup_cat_others")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            progress = get_progress_bar(state.get('current_step', 1))
            message = (
                f"🎮 **SUPORTE GAMER ONCABO**\n\n"
                f"Olá! Fico feliz em te ajudar! 😊\n\n"
                f"Vou te guiar passo a passo para resolver seu problema da melhor forma.\n\n"
                f"{progress} - **Tipo do Problema**\n\n"
                f"Primeiro, me conta: qual dessas opções descreve melhor o que está acontecendo?"
            )

            await context.bot.send_message(
                chat_id=user.id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"Usuário {user.id} iniciou fluxo de suporte.")

        except Exception as e:
            logger.error(f"Erro no comando /suporte: {e}", exc_info=True)
            if update.effective_user:
                await context.bot.send_message(chat_id=update.effective_user.id, text="❌ Erro ao iniciar suporte. Tente novamente.")

    async def handle_status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa o comando /status com lógica contextual (grupo vs. privado)."""
        try:
            await self._ensure_initialized()
            user = update.effective_user
            if not user:
                return

            # Guarda de verificação: redireciona se for usuário não verificado no grupo
            if not await self._check_and_redirect_unverified_group_user(update, context):
                return

            chat_id = update.effective_chat.id
            is_group = chat_id != user.id

            # Lógica para quando o comando é usado em um grupo
            if is_group:
                await update.message.delete()
                active_tickets = await self._get_user_active_tickets(user.id)

                if not active_tickets:
                    message = f"👋 Olá, {user.mention_markdown()}! Você não possui atendimentos ativos no momento."
                    reply_markup = None
                else:
                    latest_ticket = active_tickets[0]
                    protocol = latest_ticket.get('protocol', 'N/A')
                    status_display = latest_ticket.get('status_display', 'N/A')
                    message = (
                        f"👋 Olá, {user.mention_markdown()}!\n\n"
                        f"Seu chamado mais recente (`{protocol}`) está com o status: **{status_display}**."
                    )
                    keyboard = [[InlineKeyboardButton("📋 Ver histórico completo", callback_data=f"status_show_all:{user.id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    message_thread_id=int(SUPPORT_TOPIC_ID) if SUPPORT_TOPIC_ID else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            # Lógica para quando o comando é usado no privado
            else:
                full_status_message = await self._get_full_status_message(user.id)
                await update.message.reply_text(full_status_message, parse_mode='Markdown')

    async def _get_user_active_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """Busca e retorna apenas os tickets ativos de um usuário."""
        tickets_result = await self._hubsoft_use_case.get_user_tickets(user_id)
        if not tickets_result.success:
            return []
        
        all_tickets = tickets_result.data.get('tickets', [])
        return [t for t in all_tickets if t.get('closed_at') is None]

    async def _get_full_status_message(self, user_id: int) -> str:
        """Monta a mensagem completa de status com todos os tickets."""
        tickets_result = await self._hubsoft_use_case.get_user_tickets(user_id)

        if not tickets_result.success or not tickets_result.data.get('tickets'):
            return ("📋 **Seus Atendimentos**\n\n"
                    "👋 Olá! Você ainda não tem nenhum atendimento aberto.\n\n"
                    "💡 **Precisa de ajuda?**\nUse o comando /suporte para abrir um novo chamado!")

        tickets = tickets_result.data.get('tickets', [])
        active_tickets = [t for t in tickets if t.get('closed_at') is None]
        finished_tickets = [t for t in tickets if t.get('closed_at') is not None]

        message_parts = ["📋 **Seus Atendimentos**\n"]
        message_parts.append(f"📊 **Resumo:** {len(tickets)} atendimento(s) no total\n"
                           f"🟢 Ativos: {len(active_tickets)} | ✅ Finalizados: {len(finished_tickets)}\n")

        category_names = {
            'connectivity': '🌐 Conectividade/Ping',
            'performance': '⚡ Performance/FPS',
            'game_issues': '🎮 Problemas no Jogo',
            'configuration': '💻 Configuração',
            'others': '📞 Outros'
        }

        if active_tickets:
            message_parts.append("\n🔴 **ATENDIMENTOS ATIVOS**\n")
            for ticket in active_tickets:
                days_open = 'N/A'
                if isinstance(ticket.get('created_at'), str):
                    try:
                        created_date = datetime.fromisoformat(ticket['created_at'].replace(' ', 'T'))
                        days_open = (datetime.now() - created_date).days
                    except (ValueError, TypeError): pass
                
                message_parts.append(f"\n{self._get_status_emoji(ticket.get('status_key'))} **{ticket.get('protocol', 'N/A')}**\n"
                                   f"   📂 {category_names.get(ticket['category'], ticket['category'])} | 📅 {ticket.get('status_display', 'N/A')} • Aberto há {days_open} dia(s)\n")

        if finished_tickets:
            message_parts.append("\n✅ **ÚLTIMOS ATENDIMENTOS FINALIZADOS**\n")
            for ticket in finished_tickets[:3]:
                message_parts.append(f"\n{self._get_status_emoji(ticket.get('status_key'))} **{ticket.get('protocol', 'N/A')}**\n"
                                   f"   📂 {category_names.get(ticket['category'], ticket['category'])} | 🏁 Status: {ticket.get('status_display', 'N/A')}\n")
                if ticket.get('closure_description'):
                    message_parts.append(f"   💬 **Solução:** _{ticket['closure_description']}_\n")
            
            if len(finished_tickets) > 3:
                message_parts.append(f"\n_... e mais {len(finished_tickets) - 3} finalizado(s)_\n")

        if not active_tickets:
            message_parts.append("\n💡 **Precisa de ajuda?**\nUse o comando /suporte para abrir um novo chamado!")

        return "".join(message_parts)

    async def handle_admin_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comandos administrativos."""
        await update.message.reply_text("Funcionalidade de administração em manutenção.")

    async def _handle_start_flow_support_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Inicia o fluxo de suporte a partir de um botão de callback, replicando /suporte."""
        logger.info(f"Usuário {query.from_user.id} iniciou fluxo de suporte via callback.")
        await query.message.edit_text("Iniciando o fluxo de suporte...")

        try:
            user = query.from_user

            # VALIDAÇÃO CRÍTICA: Usuário deve estar verificado.
            is_verified = await self._check_user_verified(user.id)
            if not is_verified:
                await context.bot.send_message(chat_id=user.id, text="⚠️ Sua verificação não foi encontrada. Por favor, use /start para se verificar novamente.")
                return

            # VALIDAÇÃO: Verifica se já tem ticket ativo
            active_result = await self._hubsoft_use_case.get_user_active_tickets(user.id)

            if active_result.success and active_result.data.get('has_active'):
                active_tickets = active_result.data.get('tickets', [])
                active_ticket = active_tickets[0] if active_tickets else None

                if not active_ticket:
                    logger.error(f"HubSoft retornou has_active=True mas sem tickets para user {user.id}")
                    await context.bot.send_message(chat_id=user.id, text="❌ Erro ao verificar tickets ativos. Tente novamente.")
                    return

                protocol = active_ticket.get('protocol') or f"HS-{active_ticket.get('id', 'UNKNOWN')}"
                category_names = {
                    'connectivity': '🌐 Conectividade/Ping', 'performance': '⚡ Performance/FPS',
                    'game_issues': '🎮 Problemas no Jogo', 'configuration': '💻 Configuração', 'others': '📞 Outros'
                }
                category = category_names.get(active_ticket['category'], active_ticket['category'])
                status_pt = self._get_status_name_pt(active_ticket['status'])
                user_mention = user.mention_markdown() if user.username else user.first_name

                message = (
                    f"Olá, {user_mention}! 😊\\n\\n"
                    f"🎮 Vejo que você já está sendo atendido pela nossa equipe!\\n\\n"
                    f"📋 **Protocolo:** `{protocol}`\\n"
                    f"📂 **Categoria:** {category}\\n"
                    f"📅 **Status:** {status_pt}\\n\\n"
                    f"⏰ **Nossos técnicos já estão trabalhando no seu caso!**\\n\\n"
                    f"💡 Use /status para acompanhar o andamento\\n"
                    f"🙏 Agradecemos sua paciência e confiança!"
                )
                await context.bot.send_message(chat_id=user.id, text=message, parse_mode='Markdown')
                logger.info(f"Usuário {user.id} tentou abrir ticket via callback mas já tem ativo: {protocol}")
                return

            # Inicia o fluxo de suporte (formulário) - agora no banco de dados
            await self._support_handler.start_support_flow(user.id)

            keyboard = [
                [
                    InlineKeyboardButton("🌐 Conectividade/Ping", callback_data="sup_cat_connectivity"),
                    InlineKeyboardButton("⚡ Performance/FPS", callback_data="sup_cat_performance")
                ],
                [
                    InlineKeyboardButton("🎮 Problemas no Jogo", callback_data="sup_cat_game_issues"),
                    InlineKeyboardButton("💻 Configuração", callback_data="sup_cat_configuration")
                ],
                [InlineKeyboardButton("📞 Outros", callback_data="sup_cat_others")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            progress = get_progress_bar(1)
            message = (
                f"🎮 **SUPORTE GAMER ONCABO**\\n\\n"
                f"Olá! Fico feliz em te ajudar! 😊\\n\\n"
                f"Vou te guiar passo a passo para resolver seu problema da melhor forma.\\n\\n"
                f"{progress} - **Tipo do Problema**\\n\\n"
                f"Primeiro, me conta: qual dessas opções descreve melhor o que está acontecendo?"
            )
            await context.bot.send_message(chat_id=user.id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
            logger.info(f"Usuário {user.id} iniciou fluxo de suporte via callback - Step 1 (Categoria)")

        except Exception as e:
            logger.error(f"Erro no _handle_start_flow_support_callback: {e}", exc_info=True)
            await context.bot.send_message(chat_id=query.from_user.id, text="❌ Erro ao iniciar suporte. Tente novamente.")

    async def _handle_start_flow_status_callback(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Inicia a verificação de status a partir de um botão de callback, replicando /status."""
        logger.info(f"Usuário {query.from_user.id} iniciou verificação de status via callback.")
        await query.message.edit_text("Verificando status dos seus chamados...")

        try:
            user = query.from_user

            # VALIDAÇÃO CRÍTICA: Usuário deve estar verificado.
            is_verified = await self._check_user_verified(user.id)
            if not is_verified:
                await context.bot.send_message(chat_id=user.id, text="⚠️ Sua verificação não foi encontrada. Por favor, use /start para se verificar novamente.")
                return

            # ADR-001: Busca tickets direto do HubSoft
            tickets_result = await self._hubsoft_use_case.get_user_tickets(user.id)

            if not tickets_result.success or tickets_result.data.get('count', 0) == 0:
                message = (
                    "📋 **Seus Atendimentos**\\n\\n"
                    "👋 Olá! Você ainda não tem nenhum atendimento aberto.\\n\\n"
                    "💡 **Precisa de ajuda?**\\n"
                    "Use o comando /suporte para abrir um novo chamado!\\n\\n"
                    "Nossa equipe está sempre pronta para te ajudar! 😊"
                )
                await context.bot.send_message(chat_id=user.id, text=message, parse_mode='Markdown')
                logger.info(f"Usuário {user.id} verificou status via callback - sem atendimentos")
                return

            tickets = tickets_result.data.get('tickets', [])
            active_statuses = ['pending', 'open', 'in_progress']
            active_tickets = [t for t in tickets if t.get('status') in active_statuses]
            finished_tickets = [t for t in tickets if t.get('status') not in active_statuses]

            message_parts = ["📋 **Seus Atendimentos**\\n"]
            total = len(tickets)
            active_count = len(active_tickets)
            finished_count = len(finished_tickets)

            message_parts.append(
                f"📊 **Resumo:** {total} atendimento(s) no total\\n"
                f"🟢 Ativos: {active_count} | ✅ Finalizados: {finished_count}\\n"
            )

            category_names = {
                'connectivity': '🌐 Conectividade/Ping', 'performance': '⚡ Performance/FPS',
                'game_issues': '🎮 Problemas no Jogo', 'configuration': '💻 Configuração', 'others': '📞 Outros'
            }

            if active_tickets:
                message_parts.append("\\n🔴 **ATENDIMENTOS ATIVOS**\\n")
                for ticket in active_tickets:
                    status_emoji = self._get_status_emoji(ticket['status'])
                    status_name = self._get_status_name_pt(ticket['status'])
                    protocol = ticket.get('protocol') or f"#{ticket['id']:06d}"
                    category = category_names.get(ticket['category'], ticket['category'])
                    if isinstance(ticket['created_at'], str):
                        created_date = datetime.fromisoformat(ticket['created_at'].replace(' ', 'T'))
                    else:
                        created_date = ticket['created_at']
                    days_open = (datetime.now() - created_date).days
                    message_parts.append(
                        f"\\n{status_emoji} **{protocol}**\\n"
                        f"   📂 {category}\\n"
                        f"   📅 {status_name} • Aberto há {days_open} dia(s)\\n"
                    )
                    if ticket.get('affected_game'):
                        message_parts.append(f"   🎮 {ticket['affected_game']}\\n")

            if finished_tickets:
                message_parts.append("\\n✅ **ÚLTIMOS ATENDIMENTOS FINALIZADOS**\\n")
                recent_finished = finished_tickets[:3]
                for ticket in recent_finished:
                    status_emoji = self._get_status_emoji(ticket['status'])
                    status_name = self._get_status_name_pt(ticket['status'])
                    protocol = ticket.get('protocol') or f"#{ticket['id']:06d}"
                    category = category_names.get(ticket['category'], ticket['category'])
                    message_parts.append(
                        f"\\n{status_emoji} **{protocol}**\\n"
                        f"   📂 {category}\\n"
                        f"   🏁 Status: {status_name}\\n"
                    )
                if len(finished_tickets) > 3:
                    message_parts.append(f"\\n_... e mais {len(finished_tickets) - 3} finalizado(s)_\\n")

            if not active_tickets:
                message_parts.append(
                    "\\n💡 **Precisa de ajuda?**\\n"
                    "• Use /suporte para abrir um atendimento\\n"
                )
            else:
                message_parts.append(
                    "\\n💡 **Dicas:**\\n"
                    "• Nossa equipe está trabalhando no seu atendimento\\n"
                    "• Aguarde o retorno em breve!\\n"
                )

            message = "".join(message_parts)
            await context.bot.send_message(chat_id=user.id, text=message, parse_mode='Markdown')
            logger.info(f"Usuário {user.id} verificou status via callback: {active_count} ativos, {finished_count} finalizados")

        except Exception as e:
            logger.error(f"Erro no _handle_start_flow_status_callback: {e}", exc_info=True)
            await context.bot.send_message(chat_id=query.from_user.id, text="❌ Erro ao verificar seus chamados. Tente novamente.")

    async def handle_callback_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa callbacks de botões inline."""
        try:
            await self._ensure_initialized()

            query = update.callback_query
            if not query:
                return

            await query.answer()

            callback_data = query.data
            user = query.from_user

            # Roteador de callbacks
            if callback_data.startswith("sup_"):
                await self._handle_support_callback(query, context, callback_data)
            elif callback_data.startswith("dup_resolve_"):
                await self._handle_duplicate_resolution_callback(query, context, callback_data)
            elif callback_data.startswith("resolve_dup:") or callback_data.startswith("resolve:"):
                # Novo callback de resolução proativa de duplicatas
                await self._handle_duplicate_resolution_callback(query, context, callback_data)
            elif callback_data.startswith("accept_rules_"):
                await self._handle_accept_rules_callback(query, context, callback_data)
            elif callback_data.startswith("cat_"):
                await self._handle_category_selection(query, callback_data)
            elif callback_data == "start_flow_support":
                await self._handle_start_flow_support_callback(query, context)
            elif callback_data == "start_flow_status":
                await self._handle_start_flow_status_callback(query, context)
            elif callback_data.startswith("status_show_all:"):
                await self._handle_show_all_tickets_callback(query, context, callback_data)
            else:
                logger.warning(f"Callback não reconhecido: {callback_data}")

        except Exception as e:
            logger.error(f"Erro no callback: {e}")
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Erro inesperado. Tente novamente."
                )

    async def _handle_show_all_tickets_callback(self, query: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
        """Envia a lista completa de tickets para o usuário no privado."""
        try:
            user_id = int(callback_data.split(':')[1])

            # Medida de segurança: apenas o usuário que solicitou pode acionar o botão
            if query.from_user.id != user_id:
                await query.answer("Este botão não é para você.", show_alert=True)
                return

            await query.answer("Buscando seu histórico completo...")

            # Gera a mensagem completa e envia no privado
            full_status_message = await self._get_full_status_message(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=full_status_message,
                parse_mode='Markdown'
            )

            # Edita a mensagem original no grupo para remover o botão
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ *O histórico completo foi enviado no seu privado.*",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao mostrar todos os tickets via callback: {e}", exc_info=True)
            await query.answer("❌ Erro ao buscar seu histórico.", show_alert=True)

    async def _handle_duplicate_resolution_callback(self, query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
        """
        Processa a escolha do usuário na resolução de CPF duplicado.

        Delega para CPFVerificationHandler.
        """
        await self._ensure_initialized()
        await self._cpf_handler.handle_duplicate_resolution_callback(query, context, callback_data)

    async def _handle_category_selection(self, query, callback_data: str) -> None:
        """Processa seleção de categoria de suporte."""
        category_map = {
            "cat_connectivity": "🌐 Conectividade/Ping",
            "cat_performance": "⚡ Performance/FPS",
            "cat_game_issues": "🎮 Problemas no Jogo",
            "cat_configuration": "💻 Configuração",
            "cat_others": "📞 Outros"
        }

        category_name = category_map.get(callback_data, "Outros")

        message = (
            f"📝 **Categoria Selecionada:** {category_name}\n\n"
            "Agora me conte com detalhes sobre seu problema:\n\n"
            "• Quando começou o problema?\n"
            "• Em qual jogo acontece?\n"
            "• Descrição detalhada\n\n"
            "💡 Quanto mais detalhes, melhor poderemos ajudar!"
        )

        await query.edit_message_text(
            message,
            parse_mode='Markdown'
        )

        # Aqui registraria o contexto da conversa para próximas mensagens
        # TODO: Implementar state management para conversas

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa mensagens de texto."""
        logger.info(f"handle_text_message triggered for user {update.effective_user.id} with text: '{update.message.text}'")
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            text = update.message.text

            # Verifica se está aguardando CPF (contexto de verificação ativa)
            # PRIMEIRO, checa o estado em memória (fluxo normal)
            if context.user_data.get('waiting_cpf'):
                # Validação simples para garantir que é um CPF
                if text and text.isdigit() and len(text) in [11, 14]:
                    await self._handle_cpf_input(update, context, text)
                    return

            # SEGUNDO, checa o banco de dados (fluxo proativo via checkup)
            status_info = await self._cpf_use_case.get_verification_status(user.id)
            if status_info.status == VerificationStatus.PENDING.value:
                logger.info(f"Verificação PENDENTE encontrada no DB para usuário {user.id}. Tratando texto como CPF.")
                if text and text.isdigit() and len(text) in [11, 14]:
                    await self._handle_cpf_input(update, context, text)
                    return

            # Se não está aguardando CPF, continua o fluxo normal...

            # Verifica se está em fluxo de suporte - delega para SupportFormHandler
            # O handler agora verifica internamente se há sessão ativa no banco
            handled = await self._support_handler.handle_description_input(update, context, text)
            if handled:
                return

            # PRIMEIRA INTERAÇÃO? → Inicia fluxo automático
            already_interacted = await self._user_already_interacted(user.id)
            if not already_interacted:
                logger.info(f"Primeira interação do usuário {user.id} - iniciando fluxo de verificação")
                await self._start_welcome_flow(update, context)
                return

            # Usuário já interagiu - Verifica se está realmente ativo
            is_active = await self._check_user_verified(user.id)
            if is_active:
                # Usuário verificado e ativo - outras mensagens de texto
                message = (
                    "💬 Mensagem recebida!\n\n"
                    "Para criar um atendimento, use /suporte\n"
                    "Para verificar status, use /status\n\n"
                    "📋 Digite /ajuda para ver todos os comandos."
                )
                await update.message.reply_text(message)
                return

            # Se não está ativo, busca a mensagem de status contextualizada
            status_info = await self._get_verification_status_message(user.id)

            # Garante que a flag para receber o CPF seja setada se o status for pendente
            if status_info["status"] in [VerificationStatus.PENDING.value, VerificationStatus.IN_PROGRESS.value]:
                context.user_data['waiting_cpf'] = True
                logger.debug(f"Flag waiting_cpf setado para usuário {user.id} com status {status_info['status']}")

            # BUG FIX: Verifica se a mensagem não está vazia antes de enviar
            if status_info["message"]:
                await update.message.reply_text(
                    status_info["message"],
                    parse_mode='Markdown'
                )
            else:
                # Caso de borda: usuário não está ativo mas tem verificação completa antiga.
                logger.warning(f"Usuário {user.id} em estado inconsistente (não ativo, mas com verificação completa). Guiando para /start.")
                await update.message.reply_text(
                    "Olá! Vejo que você já se verificou antes, mas algo parece estar errado com seu acesso. "
                    "Por favor, use /start para reiniciar o processo ou contate o suporte.",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Erro ao processar mensagem de texto: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar mensagem."
            )

    async def handle_photo_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa mensagens de foto (anexos)."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            # Verifica se está em fluxo de suporte - delega para SupportFormHandler
            # O handler agora verifica internamente se há sessão ativa no banco
            handled = await self._support_handler.handle_photo_attachment(update, context)
            if handled:
                return

            # Se não está em suporte, informa o usuário
            await update.message.reply_text(
                "📷 Foto recebida!\n\n"
                "Para criar um atendimento com anexos, use /suporte",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao processar foto: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar foto. Tente novamente."
            )

    async def _handle_cpf_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cpf: str) -> None:
        """
        Processa entrada de CPF e cria link de acesso ao grupo se válido.

        Delega para CPFVerificationHandler.
        """
        await self._ensure_initialized()
        await self._cpf_handler.handle_cpf_input(update, context, cpf)

    # ==================== SUPPORT FLOW HANDLERS ====================

    async def _handle_support_callback(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Router principal para callbacks do fluxo de suporte. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_callback(query, context, callback_data)

    async def _handle_support_cancel(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancela o fluxo de suporte. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_cancel(query, context)

    async def _handle_support_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Volta para etapa anterior. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_back(query, context)

    async def _handle_support_category(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de categoria. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_category(query, context, callback_data)

    async def _show_game_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de jogo. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.show_game_step(query, context)

    async def _show_category_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de categoria. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.show_category_step(query, context)

    async def _handle_support_game(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de jogo. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_game(query, context, callback_data)

    async def _show_timing_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de timing. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.show_timing_step(query, context)

    async def _handle_support_timing(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de timing. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_timing(query, context, callback_data)

    async def _show_attachments_step(self, query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de anexos opcionais. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.show_attachments_step(query_or_message, context)

    async def _handle_support_attachment_action(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa ações de anexos. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_attachment_action(query, context, callback_data)

    async def _show_confirmation_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de confirmação. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.show_confirmation_step(query, context)

    async def _handle_support_confirmation(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa confirmação de criação do ticket. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_confirmation(query, context, callback_data)

    async def _handle_support_edit(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa edição de campos. Delega para SupportFormHandler."""
        await self._ensure_initialized()
        await self._support_handler.handle_support_edit(query, context, callback_data)

    async def _create_ticket_from_support_flow(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Cria ticket a partir do fluxo de suporte. Delega para SupportFormHandler.
        """
        await self._ensure_initialized()
        await self._support_handler.create_ticket_from_support_flow(query, context)

    async def _cpf_reminder_callback(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Envia um lembrete para o usuário que não enviou o CPF a tempo.

        Delega para CPFVerificationHandler.
        """
        await self._ensure_initialized()
        await self._cpf_handler.cpf_reminder_callback(context)

    async def _is_admin(self, user_id: int) -> bool:
        """Verifica se usuário é administrador consultando o repositório."""
        # Garante que o repositório está inicializado
        if not self._admin_repo:
            await self._ensure_initialized()
        
        return await self._admin_repo.is_administrator(user_id)

    def _get_status_emoji(self, status_key: str) -> str:
        """Retorna emoji correspondente ao prefixo do status do Hubsoft."""
        status_emojis = {
            "pendente": "⏳",
            "aguardando_analise": "🔵",
            "em_atendimento": "🔄",
            "resolvido": "✅",
            "fechado": "🔒",
            "cancelado": "❌",
            # Adicione outros prefixos conforme necessário
        }
        return status_emojis.get(status_key, "❓")

    async def handle_new_member(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa entrada e saída de novos membros no grupo."""
        try:
            await self._ensure_initialized()

            if not update.chat_member:
                return

            new_member_status = update.chat_member.new_chat_member.status
            old_member_status = update.chat_member.old_chat_member.status
            user = update.chat_member.from_user
            chat = update.effective_chat

            # LÓGICA DE DESATIVAÇÃO: Usuário saiu ou foi removido
            if new_member_status in ['left', 'kicked'] and old_member_status not in ['left', 'kicked']:
                try:
                    logger.warning(f"Usuário {user.first_name} ({user.id}) saiu ou foi removido do grupo.")
                    user_repo = self._container.get("user_repository")
                    domain_user = await user_repo.find_by_telegram_id(user.id)

                    if domain_user:
                        reason = f"User left group or was kicked. Status: {new_member_status}"
                        domain_user.deactivate(reason)
                        await user_repo.save(domain_user)
                        logger.info(f"Usuário {user.id} desativado e status de regras resetado no banco de dados.")
                except Exception as deactivation_error:
                    logger.error(f"Falha ao desativar o usuário {user.id} na saída do grupo: {deactivation_error}")

            # LÓGICA DE BOAS-VINDAS: Usuário entrou no grupo
            elif new_member_status == 'member' and old_member_status in ['left', 'kicked']:
                logger.info(f"Novo membro detectado ou retornando: {user.first_name} ({user.id})")
                
                user_repo = self._container.get("user_repository")
                domain_user = await user_repo.find_by_telegram_id(user.id)

                # Inicia o fluxo de boas-vindas apenas se o usuário for novo ou se suas regras não estiverem aceitas
                if not domain_user or not domain_user.rules_accepted:
                    logger.info(f"Iniciando fluxo de boas-vindas para {user.first_name} (ID: {user.id}). Usuário novo ou regras não aceitas.")
                    
                    if hasattr(self, '_welcome_use_case') and self._welcome_use_case:
                        from ...domain.value_objects.welcome_message import WelcomeMessage
                        from ...core.config import WELCOME_TOPIC_ID, RULES_TOPIC_ID
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                        await self._welcome_use_case.handle_new_member(
                            user_id=user.id,
                            username=user.username or user.first_name,
                            first_name=user.first_name,
                            last_name=user.last_name
                        )

                        welcome_msg = WelcomeMessage.create_initial_welcome(welcome_topic_id=int(WELCOME_TOPIC_ID) if WELCOME_TOPIC_ID else None)
                        user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
                        welcome_text = welcome_msg.format_for_user(user_mention=user_mention, username=user.first_name)
                        await context.bot.send_message(
                            chat_id=chat.id,
                            text=welcome_text,
                            parse_mode='HTML',
                            message_thread_id=int(WELCOME_TOPIC_ID) if WELCOME_TOPIC_ID else None
                        )

                        if RULES_TOPIC_ID:
                            rules_msg = WelcomeMessage.create_rules_reminder(rules_topic_id=int(RULES_TOPIC_ID), user_id=user.id)
                            rules_text = rules_msg.format_for_user(user_mention=user_mention, username=user.first_name)
                            keyboard = [[InlineKeyboardButton(rules_msg.button_text, callback_data=rules_msg.button_callback)]]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await context.bot.send_message(
                                chat_id=chat.id,
                                text=rules_text,
                                parse_mode='HTML',
                                message_thread_id=int(RULES_TOPIC_ID),
                                reply_markup=reply_markup
                            )
                else:
                    logger.info(f"Membro {user.first_name} ({user.id}) já tem as regras aceitas. Pulando boas-vindas.")

        except Exception as e:
            logger.error(f"Erro ao processar novo membro: {e}")

    async def _handle_accept_rules_callback(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa callback de aceitar regras."""
        try:
            user = query.from_user

            # Extrai user_id do callback_data
            # Formato: accept_rules_{user_id}
            expected_user_id = int(callback_data.split('_')[-1])

            # Verifica se é o usuário correto
            if user.id != expected_user_id:
                await query.answer(
                    "❌ Este botão não é para você!",
                    show_alert=True
                )
                return

            # Usa WelcomeManagementUseCase
            if hasattr(self, '_welcome_use_case') and self._welcome_use_case:
                result = await self._welcome_use_case.accept_rules(
                    user_id=user.id,
                    username=user.username or user.first_name
                )

                if result.success:
                    # Atualiza mensagem
                    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

                    from ...domain.value_objects.welcome_message import WelcomeMessage
                    confirmation_msg = WelcomeMessage.create_rules_accepted()
                    confirmation_text = confirmation_msg.format_for_user(
                        user_mention=user_mention,
                        username=user.first_name
                    )

                    # Edita mensagem removendo botão
                    await query.edit_message_text(
                        text=confirmation_text,
                        parse_mode='HTML'
                    )

                    # Notifica usuário
                    await query.answer(
                        result.notification_text,
                        show_alert=True
                    )

                    logger.info(f"Regras aceitas por {user.first_name} ({user.id})")

                else:
                    await query.answer(
                        f"❌ {result.message}",
                        show_alert=True
                    )

        except Exception as e:
            logger.error(f"Erro ao processar aceitação de regras: {e}")
            await query.answer(
                "❌ Erro ao processar. Tente novamente.",
                show_alert=True
            )

    async def handle_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa erros gerais."""
        logger.error(f"Erro no bot: {context.error}")

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Ocorreu um erro inesperado. Tente novamente mais tarde."
                )
            except:
                pass  # Evita loop de erros