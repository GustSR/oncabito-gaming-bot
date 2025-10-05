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
from ...application.use_cases.admin_operations_use_case import AdminOperationsUseCase
from ...domain.value_objects.identifiers import UserId
from ...core.config import SUPPORT_TOPIC_ID, TELEGRAM_GROUP_ID

logger = logging.getLogger(__name__)


# ==================== SUPPORT CONVERSATION STATES ====================

class SupportState:
    """Estados do fluxo conversacional de suporte."""
    IDLE = "idle"
    CATEGORY = "category"
    GAME = "game"
    TIMING = "timing"
    DESCRIPTION = "description"
    ATTACHMENTS = "attachments"
    CONFIRMATION = "confirmation"


# ==================== HELPER FUNCTIONS ====================

def get_progress_bar(current_step: int, total_steps: int = 6) -> str:
    """Retorna barra de progresso visual."""
    filled = "▓" * current_step
    empty = "░" * (total_steps - current_step)
    return f"{filled}{empty} {current_step}/{total_steps}"


def get_step_status(step: int, current: int) -> str:
    """Retorna emoji de status para cada etapa."""
    if step < current:
        return "✅"
    elif step == current:
        return "🔄"
    else:
        return "⏳"


def init_support_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicializa estado do suporte no context.user_data."""
    context.user_data['support'] = {
        'state': SupportState.IDLE,
        'category': None,
        'category_name': None,
        'game': None,
        'game_name': None,
        'timing': None,
        'timing_name': None,
        'description': None,
        'attachments': [],
        'current_step': 0
    }


def get_support_state(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    """Obtém estado do suporte."""
    if 'support' not in context.user_data:
        init_support_state(context)
    return context.user_data['support']


def clear_support_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Limpa estado do suporte."""
    if 'support' in context.user_data:
        del context.user_data['support']


class TelegramBotHandler:
    """Handler principal para interações do Telegram Bot."""

    def __init__(self):
        self._container = None
        self._hubsoft_use_case: Optional[HubSoftIntegrationUseCase] = None
        self._cpf_use_case: Optional[CPFVerificationUseCase] = None
        self._admin_use_case: Optional[AdminOperationsUseCase] = None
        self._welcome_use_case = None  # WelcomeManagementUseCase
        self._admin_repo = None  # AdminRepository

    async def _ensure_initialized(self) -> None:
        """Garante que o handler está inicializado."""
        if self._container is None:
            self._container = get_container()
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")
            self._cpf_use_case = self._container.get("cpf_verification_use_case")
            self._admin_use_case = self._container.get("admin_operations_use_case")
            self._welcome_use_case = self._container.get("welcome_management_use_case")
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
        Verifica se usuário tem CPF verificado e está autorizado a usar comandos.

        Args:
            user_id: ID do usuário do Telegram

        Returns:
            bool: True se usuário está verificado, False caso contrário
        """
        try:
            await self._ensure_initialized()

            # Busca verificação de CPF no repositório
            cpf_repo = self._container.get("cpf_verification_repository")
            if not cpf_repo:
                logger.warning("CPF verification repository não disponível")
                return False

            # Busca verificações pelo user_id (retorna lista)
            verifications = await cpf_repo.find_by_user_id(user_id, limit=10)

            if not verifications:
                logger.debug(f"Usuário {user_id} não possui verificação de CPF")
                return False

            # Busca verificação completed (importa VerificationStatus se necessário)
            from ...domain.entities.cpf_verification import VerificationStatus
            verification = next((v for v in verifications if v.status == VerificationStatus.COMPLETED), None)

            if not verification:
                logger.debug(f"Usuário {user_id} possui verificações mas nenhuma completed")
                return False

            logger.debug(f"Usuário {user_id} está verificado")
            return True

        except Exception as e:
            logger.error(f"Erro ao verificar usuário {user_id}: {e}")
            return False

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
                # Apresentação do OnCabito e solicitação de CPF
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

                # CRÍTICO: Cria verificação pendente no banco ANTES de pedir CPF
                logger.info(f"Criando verificação pendente para usuário {user.id}")
                verification_result = await self._cpf_use_case.start_verification(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    user_mention=f"<a href='tg://user?id={user.id}'>{user.first_name}</a>",
                    verification_type="auto_checkup",
                    source_action="/start command"
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

                logger.info(f"Usuário {user.id} iniciou conversa privada - aguardando CPF")
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
            logger.error(f"Erro no comando /start: {e}")
            await update.message.reply_text(
                "❌ Ocorreu um erro inesperado. Tente novamente mais tarde."
            )

    async def handle_support_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /suporte - Inicia fluxo conversacional."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            chat_id = update.effective_chat.id
            is_group = chat_id != user.id

            if not user:
                return

            # VALIDAÇÃO CRÍTICA: Verifica se usuário tem CPF verificado
            is_verified = await self._check_user_verified(user.id)
            if not is_verified:
                # Usuário não verificado - inicia fluxo de boas-vindas automaticamente
                await self._start_welcome_flow(update, context)
                logger.info(f"Usuário {user.id} tentou usar /suporte sem estar verificado - iniciado fluxo de boas-vindas")
                return

            # VALIDAÇÃO: No grupo, só funciona no tópico Suporte Gamer
            if is_group:
                from ...core.config import SUPPORT_TOPIC_ID
                message_thread_id = update.effective_message.message_thread_id

                if SUPPORT_TOPIC_ID and str(message_thread_id) != str(SUPPORT_TOPIC_ID):
                    # Comando usado fora do tópico correto - ignora silenciosamente
                    logger.debug(f"Comando /suporte ignorado - tópico errado (recebido: {message_thread_id}, esperado: {SUPPORT_TOPIC_ID})")
                    return

            # VALIDAÇÃO: Verifica se já tem ticket ativo
            # ADR-001: Busca tickets ativos direto do HubSoft (Single Source of Truth)
            active_result = await self._hubsoft_use_case.get_user_active_tickets(user.id)

            if active_result.success and active_result.data.get('has_active'):
                # Já tem atendimento ativo - não pode abrir outro
                active_tickets = active_result.data.get('tickets', [])
                active_ticket = active_tickets[0] if active_tickets else None

                if not active_ticket:
                    logger.error(f"HubSoft retornou has_active=True mas sem tickets para user {user.id}")
                    await update.message.reply_text("❌ Erro ao verificar tickets ativos. Tente novamente.")
                    return

                protocol = active_ticket.get('protocol') or active_ticket.get('hubsoft_protocol') or f"HS-{active_ticket.get('id', 'UNKNOWN')}"

                category_names = {
                    'connectivity': '🌐 Conectividade/Ping',
                    'performance': '⚡ Performance/FPS',
                    'game_issues': '🎮 Problemas no Jogo',
                    'configuration': '💻 Configuração',
                    'others': '📞 Outros'
                }
                category = category_names.get(active_ticket['category'], active_ticket['category'])
                status_pt = self._get_status_name_pt(active_ticket['status'])

                # Menção ao usuário
                user_mention = user.mention_markdown() if user.username else user.first_name

                message = (
                    f"Olá, {user_mention}! 😊\n\n"
                    f"🎮 Vejo que você já está sendo atendido pela nossa equipe!\n\n"
                    f"📋 **Protocolo:** `{protocol}`\n"
                    f"📂 **Categoria:** {category}\n"
                    f"📅 **Status:** {status_pt}\n\n"
                    f"⏰ **Nossos técnicos já estão trabalhando no seu caso!**\n\n"
                    f"💡 Use /status para acompanhar o andamento\n"
                    f"🙏 Agradecemos sua paciência e confiança!"
                )

                # Se for no grupo, envia no tópico de Suporte Gamer
                send_params = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }

                if is_group:
                    from ...core.config import SUPPORT_TOPIC_ID
                    if SUPPORT_TOPIC_ID:
                        send_params['message_thread_id'] = int(SUPPORT_TOPIC_ID)

                await context.bot.send_message(**send_params)

                logger.info(f"Usuário {user.id} tentou abrir ticket mas já tem ativo: {protocol} (enviado no {'grupo/tópico' if is_group else 'privado'})")
                return

            # Se foi enviado no grupo, envia notificação ao tópico
            if is_group:
                try:
                    # Deleta o comando do grupo
                    await update.message.delete()

                    # Envia notificação ao tópico de suporte
                    await context.bot.send_message(
                        chat_id=int(TELEGRAM_GROUP_ID),
                        message_thread_id=int(SUPPORT_TOPIC_ID),
                        text=(
                            f"👋 Olá @{user.username or user.first_name}!\n\n"
                            f"Recebi seu pedido de suporte! Vou te atender no **privado** para "
                            f"entender melhor seu problema e te ajudar da melhor forma possível. 😊\n\n"
                            f"📱 Por favor, confira suas **mensagens diretas** comigo!\n\n"
                            f"💬 Te vejo lá! Já estou te aguardando..."
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Erro ao enviar notificação no tópico: {e}")

            # Inicializa estado do suporte
            init_support_state(context)
            state = get_support_state(context)
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1

            # Monta teclado de categorias
            keyboard = [
                [
                    InlineKeyboardButton("🌐 Conectividade/Ping", callback_data="sup_cat_connectivity"),
                    InlineKeyboardButton("⚡ Performance/FPS", callback_data="sup_cat_performance")
                ],
                [
                    InlineKeyboardButton("🎮 Problemas no Jogo", callback_data="sup_cat_game_issues"),
                    InlineKeyboardButton("💻 Configuração", callback_data="sup_cat_configuration")
                ],
                [
                    InlineKeyboardButton("📞 Outros", callback_data="sup_cat_others")
                ],
                [
                    InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            progress = get_progress_bar(1)
            message = (
                f"🎮 **SUPORTE GAMER ONCABO**\n\n"
                f"Olá! Fico feliz em te ajudar! 😊\n\n"
                f"Vou te guiar passo a passo para resolver seu problema da melhor forma.\n\n"
                f"{progress} - **Tipo do Problema**\n\n"
                f"Primeiro, me conta: qual dessas opções descreve melhor o que está acontecendo?"
            )

            # SEMPRE responde no privado do usuário
            await context.bot.send_message(
                chat_id=user.id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} iniciou fluxo de suporte - Step 1 (Categoria)")

        except Exception as e:
            logger.error(f"Erro no comando /suporte: {e}")
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text="❌ Erro ao iniciar suporte. Tente novamente."
                )
            except Exception as e:
                # Ignora falhas ao enviar mensagem de erro (último recurso)
                logger.error(f"Failed to send error message: {e}")
                pass

    async def handle_status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /status."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            # VALIDAÇÃO CRÍTICA: Verifica se usuário tem CPF verificado
            is_verified = await self._check_user_verified(user.id)
            if not is_verified:
                # Usuário não verificado - inicia fluxo de boas-vindas automaticamente
                await self._start_welcome_flow(update, context)
                logger.info(f"Usuário {user.id} tentou usar /status sem estar verificado - iniciado fluxo de boas-vindas")
                return

            # VALIDAÇÃO: No grupo, só funciona no tópico Suporte Gamer
            chat_id = update.effective_chat.id
            is_group = chat_id != user.id

            if is_group:
                from ...core.config import SUPPORT_TOPIC_ID
                message_thread_id = update.effective_message.message_thread_id

                if SUPPORT_TOPIC_ID and str(message_thread_id) != str(SUPPORT_TOPIC_ID):
                    # Comando usado fora do tópico correto - ignora silenciosamente
                    logger.debug(f"Comando /status ignorado - tópico errado (recebido: {message_thread_id}, esperado: {SUPPORT_TOPIC_ID})")
                    return

            # ADR-001: Busca tickets direto do HubSoft (Single Source of Truth)
            tickets_result = await self._hubsoft_use_case.get_user_tickets(user.id)

            if not tickets_result.success or tickets_result.data.get('count', 0) == 0:
                # Usuário não tem nenhum atendimento
                message = (
                    "📋 **Seus Atendimentos**\n\n"
                    "👋 Olá! Você ainda não tem nenhum atendimento aberto.\n\n"
                    "💡 **Precisa de ajuda?**\n"
                    "Use o comando /suporte para abrir um novo chamado!\n\n"
                    "Nossa equipe está sempre pronta para te ajudar! 😊"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                logger.info(f"Usuário {user.id} verificou status - sem atendimentos")
                return

            # Extrai lista de tickets do resultado
            tickets = tickets_result.data.get('tickets', [])

            # Separa tickets ativos e finalizados
            active_statuses = ['pending', 'open', 'in_progress']
            active_tickets = [t for t in tickets if t.get('status') in active_statuses]
            finished_tickets = [t for t in tickets if t.get('status') not in active_statuses]

            # Monta mensagem com lista de atendimentos
            message_parts = ["📋 **Seus Atendimentos**\n"]

            # Resumo geral
            total = len(tickets)
            active_count = len(active_tickets)
            finished_count = len(finished_tickets)

            message_parts.append(
                f"📊 **Resumo:** {total} atendimento(s) no total\n"
                f"🟢 Ativos: {active_count} | ✅ Finalizados: {finished_count}\n"
            )

            # Mapeia categorias para nomes amigáveis
            category_names = {
                'connectivity': '🌐 Conectividade/Ping',
                'performance': '⚡ Performance/FPS',
                'game_issues': '🎮 Problemas no Jogo',
                'configuration': '💻 Configuração',
                'others': '📞 Outros'
            }

            # Lista atendimentos ativos
            if active_tickets:
                message_parts.append("\n🔴 **ATENDIMENTOS ATIVOS**\n")
                for ticket in active_tickets:
                    status_emoji = self._get_status_emoji(ticket['status'])
                    status_name = self._get_status_name_pt(ticket['status'])
                    protocol = ticket.get('protocol') or f"#{ticket['id']:06d}"
                    category = category_names.get(ticket['category'], ticket['category'])

                    # Calcula dias abertos
                    if isinstance(ticket['created_at'], str):
                        created_date = datetime.fromisoformat(ticket['created_at'].replace(' ', 'T'))
                    else:
                        created_date = ticket['created_at']
                    days_open = (datetime.now() - created_date).days

                    message_parts.append(
                        f"\n{status_emoji} **{protocol}**\n"
                        f"   📂 {category}\n"
                        f"   📅 {status_name} • Aberto há {days_open} dia(s)\n"
                    )

                    if ticket.get('affected_game'):
                        message_parts.append(f"   🎮 {ticket['affected_game']}\n")

            # Lista últimos 3 atendimentos finalizados
            if finished_tickets:
                message_parts.append("\n✅ **ÚLTIMOS ATENDIMENTOS FINALIZADOS**\n")
                recent_finished = finished_tickets[:3]

                for ticket in recent_finished:
                    status_emoji = self._get_status_emoji(ticket['status'])
                    status_name = self._get_status_name_pt(ticket['status'])
                    protocol = ticket.get('protocol') or f"#{ticket['id']:06d}"
                    category = category_names.get(ticket['category'], ticket['category'])

                    message_parts.append(
                        f"\n{status_emoji} **{protocol}**\n"
                        f"   📂 {category}\n"
                        f"   🏁 Status: {status_name}\n"
                    )

                if len(finished_tickets) > 3:
                    message_parts.append(f"\n_... e mais {len(finished_tickets) - 3} finalizado(s)_\n")

            # Rodapé com dicas
            if not active_tickets:
                # Só mostra opção de abrir atendimento se NÃO tiver atendimentos ativos
                message_parts.append(
                    "\n💡 **Precisa de ajuda?**\n"
                    "• Use /suporte para abrir um atendimento\n"
                    "• Nossa equipe trabalha 24/7 para te atender!\n\n"
                    "🙏 Estamos aqui para ajudar!"
                )
            else:
                message_parts.append(
                    "\n💡 **Dicas:**\n"
                    "• Nossa equipe está trabalhando no seu atendimento\n"
                    "• Aguarde o retorno em breve!\n\n"
                    "🙏 Agradecemos sua paciência e confiança!"
                )

            message = "".join(message_parts)

            # NÃO exibe botões - apenas mensagem informativa
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

            logger.info(
                f"Usuário {user.id} verificou status: "
                f"{active_count} ativos, {finished_count} finalizados"
            )

        except Exception as e:
            logger.error(f"Erro no comando /status: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ **Ops! Algo deu errado...**\n\n"
                "Não consegui buscar seus tickets no momento.\n"
                "Por favor, tente novamente em alguns instantes.\n\n"
                "Se o problema persistir, entre em contato com nossa equipe! 🙏"
            )

    async def handle_admin_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comandos administrativos."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            # Verifica se é admin (implementar validação real)
            if not await self._is_admin(user.id):
                await update.message.reply_text("❌ Acesso negado.")
                return

            # Menu administrativo
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
                "⚙️ **Painel Administrativo**\n\n"
                "Selecione uma opção:"
            )

            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            logger.info(f"Admin {user.id} acessou painel administrativo")

        except Exception as e:
            logger.error(f"Erro no comando admin: {e}")
            await update.message.reply_text(
                "❌ Erro no painel administrativo."
            )

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
            elif callback_data.startswith("accept_rules_"):
                await self._handle_accept_rules_callback(query, context, callback_data)
            elif callback_data.startswith("cat_"):
                await self._handle_category_selection(query, callback_data)
            elif callback_data.startswith("admin_"):
                await self._handle_admin_callback(query, callback_data)
            else:
                logger.warning(f"Callback não reconhecido: {callback_data}")

        except Exception as e:
            logger.error(f"Erro no callback: {e}")
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Erro inesperado. Tente novamente."
                )

    async def _handle_duplicate_resolution_callback(self, query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
        """Processa a escolha do usuário na resolução de CPF duplicado."""
        parts = callback_data.split('_')
        action = parts[2]
        verification_id = parts[3]

        await query.edit_message_text("⏳ Processando sua escolha...", parse_mode='Markdown')

        if action == "merge":
            logger.info(f"Usuário {query.from_user.id} escolheu 'merge' para a verificação {verification_id}.")
            
            # Pega os detalhes do conflito salvos no contexto
            resolution_context = context.user_data.get('duplicate_resolution_context')
            if not resolution_context or resolution_context.get('verification_id') != verification_id:
                await query.edit_message_text("❌ Ops! Perdi o contexto desta conversa. Por favor, tente verificar seu CPF novamente.")
                return

            duplicate_users = resolution_context.get('conflicting_users', [])
            duplicate_user_ids = [u.get('user_id') for u in duplicate_users]

            # Chama o Use Case para resolver o conflito
            result = await self._cpf_use_case.resolve_duplicate_conflict(
                verification_id=verification_id,
                primary_user_id=query.from_user.id,
                duplicate_user_ids=duplicate_user_ids
            )

            if result.success and result.data.get('verified'):
                # A resolução foi um sucesso e a verificação foi completada.
                try:
                    from ...core.config import TELEGRAM_GROUP_ID
                    client_name = query.from_user.first_name
                    invite_link = await query.get_bot().create_chat_invite_link(
                        chat_id=int(TELEGRAM_GROUP_ID),
                        member_limit=1,
                        name=f"Link para {client_name}"
                    )
                    message = (
                        f"✅ **Conflito Resolvido!**\n\n"
                        f"O CPF foi associado à sua conta e removido da(s) conta(s) antiga(s).\n\n"
                        f"Seja bem-vindo(a) ao grupo!\n\n"
                        f"🔗 **Seu novo link de acesso:**\n{invite_link.invite_link}"
                    )
                    await query.edit_message_text(message, parse_mode='Markdown', disable_web_page_preview=True)
                except Exception as e:
                    logger.error(f"Erro ao criar link de convite pós-resolução de conflito: {e}")
                    await query.edit_message_text("✅ Conflito resolvido, mas houve um erro ao gerar seu link de convite. Por favor, contate o suporte.")
            else:
                # A resolução falhou
                await query.edit_message_text(f"❌ Ops! Ocorreu um erro ao tentar resolver o conflito: {result.message}. Por favor, contate o suporte.")

            # Limpa o contexto da resolução
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']

        elif action == "cancel":
            logger.info(f"Usuário {query.from_user.id} cancelou a resolução de conflito para a verificação {verification_id}.")
            # TODO: Chamar use case para cancelar a verificação
            await query.edit_message_text(
                "Ok, operação cancelada. Você pode tentar a verificação novamente com um CPF diferente, ou usar o comando /start para recomeçar."
            )

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

    async def _handle_admin_callback(self, query, callback_data: str) -> None:
        """Processa callbacks administrativos."""
        user = query.from_user

        if not await self._is_admin(user.id):
            await query.edit_message_text("❌ Acesso negado.")
            return

        if callback_data == "admin_list_tickets":
            # Lista tickets via admin use case
            result = await self._admin_use_case.list_tickets_with_filters(
                admin_user_id=user.id,
                status_filter=None,
                limit=10
            )

            if result.success:
                message = (
                    "📋 **Tickets Recentes**\n\n"
                    f"✅ Encontrados {result.affected_items} tickets\n\n"
                    "⚠️ Visualização detalhada em desenvolvimento"
                )
            else:
                message = f"❌ Erro: {result.message}"

        elif callback_data == "admin_stats":
            # Obtém estatísticas via admin use case
            result = await self._admin_use_case.get_comprehensive_stats(
                admin_user_id=user.id,
                include_details=False,
                date_range_days=7
            )

            if result.success and result.data:
                message = (
                    "📊 **Estatísticas do Sistema**\n\n"
                    f"📅 Últimos {result.data.get('period_days', 7)} dias\n\n"
                    "⚠️ Dados detalhados em desenvolvimento"
                )
            else:
                message = f"❌ Erro: {result.message}"

        elif callback_data == "admin_sync":
            message = (
                "🔄 **Sincronização HubSoft**\n\n"
                "Funcionalidade de sync disponível em breve.\n\n"
                "🚧 Sistema em migração para nova arquitetura"
            )

        elif callback_data == "admin_config":
            message = (
                "⚙️ **Configurações do Sistema**\n\n"
                "Painel de configurações em desenvolvimento.\n\n"
                "📋 Use comandos administrativos por enquanto"
            )

        else:
            message = "❓ Opção não reconhecida."

        await query.edit_message_text(
            message,
            parse_mode='Markdown'
        )

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa mensagens de texto."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            text = update.message.text

            # Verifica se está em fluxo de suporte (usuário verificado)
            if 'support' in context.user_data:
                state = get_support_state(context)

                # Se está aguardando descrição
                if state['state'] == SupportState.DESCRIPTION:
                    # Valida descrição mínima
                    if len(text.strip()) < 10:
                        await update.message.reply_text(
                            "❌ **Ops! Descrição muito curta...**\n\n"
                            "Preciso que você escreva pelo menos **10 caracteres** para "
                            "entender melhor seu problema. 😊\n\n"
                            "💡 **Dica:** Tenta me explicar o que está acontecendo com mais detalhes. "
                            "Quanto mais informações, melhor!\n\n"
                            "Pode tentar de novo? Estou aguardando! 👂",
                            parse_mode='Markdown'
                        )
                        return

                    # Salva descrição
                    state['description'] = text.strip()
                    state['state'] = SupportState.ATTACHMENTS
                    state['current_step'] = 5

                    # Mostra etapa de anexos
                    await self._show_attachments_step(update.message, context)
                    logger.info(f"Usuário {user.id} enviou descrição ({len(text)} chars)")
                    return

            # Verifica se está aguardando CPF (contexto de verificação ativa)
            if context.user_data.get('waiting_cpf') and text and text.isdigit() and len(text) == 11:
                await self._handle_cpf_input(update, context, text)
                return

            # PRIMEIRA INTERAÇÃO? → Inicia fluxo automático
            already_interacted = await self._user_already_interacted(user.id)
            if not already_interacted:
                logger.info(f"Primeira interação do usuário {user.id} - iniciando fluxo de verificação")
                await self._start_welcome_flow(update, context)
                return

            # Usuário já interagiu - Verifica se está verificado
            is_verified = await self._check_user_verified(user.id)
            if not is_verified:
                # Já interagiu mas não completou verificação
                await update.message.reply_text(
                    "⚠️ Seu cadastro ainda está em análise.\n\n"
                    "Aguarde a verificação ser concluída para usar os comandos.\n\n"
                    "Digite /ajuda se precisar de mais informações.",
                    parse_mode='HTML'
                )
                return

            # Usuário verificado - outras mensagens de texto
            message = (
                "💬 Mensagem recebida!\n\n"
                "Para criar um atendimento, use /suporte\n"
                "Para verificar status, use /status\n\n"
                "📋 Digite /ajuda para ver todos os comandos."
            )

            await update.message.reply_text(message)

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

            # Verifica se está em fluxo de suporte e aguardando anexos
            if 'support' not in context.user_data:
                await update.message.reply_text(
                    "📷 Foto recebida!\n\n"
                    "Para criar um atendimento com anexos, use /suporte",
                    parse_mode='Markdown'
                )
                return

            state = get_support_state(context)

            # Só aceita fotos na etapa de anexos
            if state['state'] != SupportState.ATTACHMENTS:
                await update.message.reply_text(
                    "📷 Aguarde o momento correto para enviar anexos.\n\n"
                    "Continue o fluxo de suporte primeiro.",
                    parse_mode='Markdown'
                )
                return

            # Verifica limite de anexos
            attachments = state.get('attachments', [])
            if len(attachments) >= 3:
                await update.message.reply_text(
                    "❌ Limite de 3 anexos atingido!\n\n"
                    "Clique em **Continuar** para prosseguir.",
                    parse_mode='Markdown'
                )
                return

            # Pega a maior resolução da foto
            photo = update.message.photo[-1]

            # Salva informações do anexo
            attachment_info = {
                'file_id': photo.file_id,
                'file_size': photo.file_size,
                'width': photo.width,
                'height': photo.height
            }

            attachments.append(attachment_info)
            state['attachments'] = attachments

            attachments_count = len(attachments)

            # Mensagem de confirmação
            remaining = 3 - attachments_count
            await update.message.reply_text(
                f"✅ **Anexo {attachments_count}/3 recebido com sucesso!**\n\n"
                f"📸 Perfeito! Você ainda pode enviar mais **{remaining} foto(s)** se quiser, "
                f"ou clicar em **Continuar** para finalizar! 😊",
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} enviou anexo {attachments_count}/3")

        except Exception as e:
            logger.error(f"Erro ao processar foto: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar foto. Tente novamente."
            )

    async def _handle_cpf_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cpf: str) -> None:
        """Processa entrada de CPF e cria link de acesso ao grupo se válido."""
        user = update.effective_user
        chat = update.effective_chat

        try:
            from ...core.config import (
                ONCABO_SITE_URL,
                ONCABO_WHATSAPP_URL,
                TELEGRAM_GROUP_ID,
                INVITE_LINK_EXPIRE_TIME
            )

            processing_msg = await update.message.reply_text(
                "🔍 <b>Verificando seu CPF...</b>\n\n"
                "Aguarde um momento enquanto consulto nossa base de dados.",
                parse_mode='HTML'
            )

            result = await self._cpf_use_case.submit_cpf(
                user_id=user.id,
                username=user.username or user.first_name,
                cpf=cpf
            )

            await processing_msg.delete()

            if result.success:
                # CASO 1: Conflito de CPF Duplicado
                if result.data.get('status') == 'conflict_detected':
                    conflict_details = result.data.get('conflict_details', {})
                    conflicting_users = conflict_details.get('users', [])
                    
                    if conflicting_users:
                        conflicting_user = conflicting_users[0]
                        conflicting_username = conflicting_user.get('username', 'outro usuário')
                        
                        message = (
                            "⚠️ **Conflito de CPF Encontrado** ⚠️\n\n"
                            f"Olá! Verifiquei que este CPF já está associado à conta **@{conflicting_username}**.\n\n"
                            "Para garantir a segurança, cada CPF só pode estar vinculado a um único usuário no Telegram.\n\n"
                            "**O que você gostaria de fazer?**"
                        )
                        
                        verification_id = result.verification_id 
                        
                        keyboard = [[
                            InlineKeyboardButton(
                                "✅ Usar nesta conta (remover da antiga)", 
                                callback_data=f"dup_resolve_merge_{verification_id}"
                            )],[
                            InlineKeyboardButton(
                                "❌ Cancelar e tentar outro CPF", 
                                callback_data=f"dup_resolve_cancel_{verification_id}"
                            )
                        ]]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # Salva o contexto para o callback
                        context.user_data['duplicate_resolution_context'] = {
                            'verification_id': verification_id,
                            'conflicting_users': conflicting_users
                        }

                        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                        logger.info(f"Conflito de CPF para user {user.id}. Iniciando fluxo de resolução.")
                    else:
                        await update.message.reply_text("❌ Encontrei um conflito com este CPF, mas não consegui obter os detalhes. Por favor, contate o suporte.")

                # CASO 2: Sucesso na Verificação (Caminho Feliz)
                elif result.data.get('verified'):
                    client_data = result.data.get('client_data', {})
                    client_name = client_data.get('name', user.first_name)
                    try:
                        invite_link = await update.get_bot().create_chat_invite_link(
                            chat_id=int(TELEGRAM_GROUP_ID),
                            member_limit=1,
                            name=f"Link para {client_name}"
                        )
                        message = (
                            f"✅ <b>PARABÉNS, {client_name}!</b> 🎉\n\n"
                            "Seu plano OnCabo Gaming está ativo e verificado com sucesso!\n\n"
                            "🔗 **LINK DE ACESSO AO GRUPO:**\n"
                            f"{invite_link.invite_link}\n\n"
                            "⏰ <b>Atenção:</b> Este link é pessoal e pode ser usado <b>apenas 1 vez</b>!\n\n"
                            "Clique no link para entrar no grupo. Nos vemos lá! 🔥"
                        )
                        logger.info(f"Link temporário criado para {user.id} ({client_name})")
                    except Exception as link_error:
                        logger.error(f"Erro ao criar link de convite: {link_error}")
                        message = "✅ **CPF Verificado!** 🎉\n\nSeu plano está ativo, mas houve um erro ao gerar seu link de convite. Por favor, contate o suporte."
                    
                    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)

            # CASO 3: Falha na Verificação (Contrato inativo, etc.)
            else:
                message = (
                    "❌ <b>Ops! Não encontrei seu CPF vinculado a um plano OnCabo Gaming ativo.</b>\n\n"
                    "Infelizmente, o acesso ao grupo é exclusivo para assinantes do plano OnCabo Gaming.\n\n"
                    "📌 <b>QUER FAZER PARTE?</b>\n"
                    f"Acesse nosso site em {ONCABO_SITE_URL} ou fale conosco pelo WhatsApp em {ONCABO_WHATSAPP_URL} para contratar e entrar na comunidade!\n\n"
                    "Estamos te esperando! 🚀"
                )
                await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=False)

            # Limpa estado de aguardando CPF
            if 'waiting_cpf' in context.user_data:
                del context.user_data['waiting_cpf']

        except Exception as e:
            logger.error(f"Erro ao processar CPF: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ <b>Erro ao verificar CPF.</b>\n\n"
                "Tente novamente ou entre em contato com o suporte.",
                parse_mode='HTML'
            )

    # ==================== SUPPORT FLOW HANDLERS ====================

    async def _handle_support_callback(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Router principal para callbacks do fluxo de suporte."""
        # Cancel
        if callback_data == "sup_cancel":
            await self._handle_support_cancel(query, context)
        # Back
        elif callback_data == "sup_back":
            await self._handle_support_back(query, context)
        # Category selection
        elif callback_data.startswith("sup_cat_"):
            await self._handle_support_category(query, context, callback_data)
        # Game selection
        elif callback_data.startswith("sup_game_"):
            await self._handle_support_game(query, context, callback_data)
        # Timing selection
        elif callback_data.startswith("sup_timing_"):
            await self._handle_support_timing(query, context, callback_data)
        # Attachments
        elif callback_data.startswith("sup_att_"):
            await self._handle_support_attachment_action(query, context, callback_data)
        # Confirmation
        elif callback_data.startswith("sup_confirm_"):
            await self._handle_support_confirmation(query, context, callback_data)
        # Edit
        elif callback_data.startswith("sup_edit_"):
            await self._handle_support_edit(query, context, callback_data)
        else:
            logger.warning(f"Callback de suporte não reconhecido: {callback_data}")

    async def _handle_support_cancel(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancela o fluxo de suporte."""
        clear_support_state(context)
        await query.edit_message_text(
            "❌ **Formulário Cancelado**\n\n"
            "Você pode iniciar um novo chamado a qualquer momento usando /suporte",
            parse_mode='Markdown'
        )
        logger.info(f"Usuário {query.from_user.id} cancelou o fluxo de suporte")

    async def _handle_support_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Volta para etapa anterior."""
        state = get_support_state(context)
        current_state = state['state']

        # Define para onde voltar
        if current_state == SupportState.GAME:
            # Volta para categoria
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1
            await self._show_category_step(query, context)
        elif current_state == SupportState.TIMING:
            # Volta para jogo
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self._show_game_step(query, context)
        elif current_state == SupportState.ATTACHMENTS:
            # Volta para timing
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self._show_timing_step(query, context)
        elif current_state == SupportState.CONFIRMATION:
            # Volta para attachments
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5
            await self._show_attachments_step(query, context)
        else:
            await query.answer("Não é possível voltar nesta etapa")

    async def _handle_support_category(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de categoria."""
        category_key = callback_data.replace("sup_cat_", "")

        category_names = {
            "connectivity": "🌐 Conectividade/Ping",
            "performance": "⚡ Performance/FPS",
            "game_issues": "🎮 Problemas no Jogo",
            "configuration": "💻 Configuração",
            "others": "📞 Outros"
        }

        state = get_support_state(context)
        state['category'] = category_key
        state['category_name'] = category_names.get(category_key, "Outros")
        state['state'] = SupportState.GAME
        state['current_step'] = 2

        await self._show_game_step(query, context)
        logger.info(f"Usuário {query.from_user.id} selecionou categoria: {category_key}")

    async def _show_game_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de jogo."""
        state = get_support_state(context)

        keyboard = [
            [
                InlineKeyboardButton("⚡️ Valorant", callback_data="sup_game_valorant"),
                InlineKeyboardButton("🔫 CS:GO", callback_data="sup_game_csgo")
            ],
            [
                InlineKeyboardButton("🎯 League of Legends", callback_data="sup_game_lol"),
                InlineKeyboardButton("🎮 Fortnite", callback_data="sup_game_fortnite")
            ],
            [
                InlineKeyboardButton("🏆 Apex Legends", callback_data="sup_game_apex"),
                InlineKeyboardButton("🌍 GTA V Online", callback_data="sup_game_gta")
            ],
            [
                InlineKeyboardButton("📱 Mobile Games", callback_data="sup_game_mobile"),
                InlineKeyboardButton("🎪 Outro jogo", callback_data="sup_game_other")
            ],
            [
                InlineKeyboardButton("◀️ Voltar", callback_data="sup_back"),
                InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = get_progress_bar(2)
        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"✅ Categoria: {state['category_name']}\n\n"
            f"{progress} - **Jogo Afetado**\n\n"
            f"Ótimo! Agora me conta: qual desses jogos está te dando dor de cabeça? 🎮"
        )

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _show_category_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de categoria."""
        keyboard = [
            [
                InlineKeyboardButton("🌐 Conectividade/Ping", callback_data="sup_cat_connectivity"),
                InlineKeyboardButton("⚡ Performance/FPS", callback_data="sup_cat_performance")
            ],
            [
                InlineKeyboardButton("🎮 Problemas no Jogo", callback_data="sup_cat_game_issues"),
                InlineKeyboardButton("💻 Configuração", callback_data="sup_cat_configuration")
            ],
            [
                InlineKeyboardButton("📞 Outros", callback_data="sup_cat_others")
            ],
            [
                InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = get_progress_bar(1)
        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"{progress} - Categoria do Problema\n\n"
            f"Selecione a categoria que melhor descreve seu problema:"
        )

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _handle_support_game(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de jogo."""
        game_key = callback_data.replace("sup_game_", "")

        game_names = {
            "valorant": "⚡️ Valorant",
            "csgo": "🔫 CS:GO",
            "lol": "🎯 League of Legends",
            "fortnite": "🎮 Fortnite",
            "apex": "🏆 Apex Legends",
            "gta": "🌍 GTA V Online",
            "mobile": "📱 Mobile Games",
            "other": "🎪 Outro jogo"
        }

        state = get_support_state(context)
        state['game'] = game_key
        state['game_name'] = game_names.get(game_key, "Outro")
        state['state'] = SupportState.TIMING
        state['current_step'] = 3

        await self._show_timing_step(query, context)
        logger.info(f"Usuário {query.from_user.id} selecionou jogo: {game_key}")

    async def _show_timing_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de timing."""
        state = get_support_state(context)

        keyboard = [
            [
                InlineKeyboardButton("🔴 Agora/Hoje", callback_data="sup_timing_now"),
                InlineKeyboardButton("📅 Ontem", callback_data="sup_timing_yesterday")
            ],
            [
                InlineKeyboardButton("📆 Esta Semana", callback_data="sup_timing_week"),
                InlineKeyboardButton("🗓️ Semana Passada", callback_data="sup_timing_lastweek")
            ],
            [
                InlineKeyboardButton("⏰ Há Muito Tempo", callback_data="sup_timing_longtime"),
                InlineKeyboardButton("♾️ Sempre Foi Assim", callback_data="sup_timing_always")
            ],
            [
                InlineKeyboardButton("◀️ Voltar", callback_data="sup_back"),
                InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = get_progress_bar(3)
        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"✅ Categoria: {state['category_name']}\n"
            f"✅ Jogo: {state['game_name']}\n\n"
            f"{progress} - **Quando Começou?**\n\n"
            f"Beleza! Agora me ajuda com uma informação importante: 🤔\n\n"
            f"Quando você notou esse problema pela primeira vez?\n"
            f"_(Isso me ajuda a entender melhor a situação!)_"
        )

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _handle_support_timing(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa seleção de timing."""
        timing_key = callback_data.replace("sup_timing_", "")

        timing_names = {
            "now": "🔴 Agora/Hoje",
            "yesterday": "📅 Ontem",
            "week": "📆 Esta Semana",
            "lastweek": "🗓️ Semana Passada",
            "longtime": "⏰ Há Muito Tempo",
            "always": "♾️ Sempre Foi Assim"
        }

        state = get_support_state(context)
        state['timing'] = timing_key
        state['timing_name'] = timing_names.get(timing_key, "Não informado")
        state['state'] = SupportState.DESCRIPTION
        state['current_step'] = 4

        # Remove o teclado e pede descrição
        progress = get_progress_bar(4)
        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"✅ Categoria: {state['category_name']}\n"
            f"✅ Jogo: {state['game_name']}\n"
            f"✅ Quando começou: {state['timing_name']}\n\n"
            f"{progress} - **Detalhes do Problema**\n\n"
            f"📝 Perfeito! Agora preciso que você me conte o que está acontecendo.\n\n"
            f"Quanto mais detalhes você me der, mais rápido conseguirei te ajudar! 💪\n\n"
            f"🔍 **Conta pra mim:**\n"
            f"• O que exatamente você está sentindo/vendo?\n"
            f"• É lag? Ping alto? Desconexões? Travamentos?\n"
            f"• Em qual servidor/região você joga?\n"
            f"• Já tentou reiniciar o roteador? Funcionou?\n"
            f"• Outros jogos ou dispositivos têm o mesmo problema?\n\n"
            f"✍️ Pode digitar sua mensagem agora, **sem pressa**! Estou aqui para te ouvir."
        )

        await query.edit_message_text(
            message,
            parse_mode='Markdown'
        )

        logger.info(f"Usuário {query.from_user.id} selecionou timing: {timing_key}")

    async def _show_attachments_step(self, query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de anexos opcionais."""
        state = get_support_state(context)
        attachments_count = len(state.get('attachments', []))

        keyboard = [
            [InlineKeyboardButton("⏭️ Pular Anexos", callback_data="sup_att_skip")],
            [InlineKeyboardButton("➡️ Continuar", callback_data="sup_att_continue")],
            [
                InlineKeyboardButton("◀️ Voltar", callback_data="sup_back"),
                InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = get_progress_bar(5)
        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"✅ Categoria: {state['category_name']}\n"
            f"✅ Jogo: {state['game_name']}\n"
            f"✅ Quando começou: {state['timing_name']}\n"
            f"✅ Descrição: \"{state['description'][:50]}...\"\n\n"
            f"{progress} - **Anexos (Opcional)**\n\n"
            f"📸 **Quer enviar prints pra me ajudar a visualizar?**\n\n"
            f"Você pode enviar até **3 imagens** (totalmente opcional!):\n"
            f"• Screenshot do ping in-game 🎯\n"
            f"• Foto do teste de velocidade 📊\n"
            f"• Print de tela com erro/problema 🖼️\n\n"
            f"Anexos enviados: **{attachments_count}/3**\n\n"
            f"💡 Isso ajuda MUITO no diagnóstico, mas se não tiver, sem problemas!\n"
            f"Pode pular e continuar. 😊"
        )

        # Verifica se é query ou message
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query_or_message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def _handle_support_attachment_action(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa ações de anexos."""
        if callback_data == "sup_att_skip" or callback_data == "sup_att_continue":
            state = get_support_state(context)
            state['state'] = SupportState.CONFIRMATION
            state['current_step'] = 6
            await self._show_confirmation_step(query, context)

    async def _show_confirmation_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de confirmação."""
        state = get_support_state(context)
        attachments_count = len(state.get('attachments', []))

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar e Criar", callback_data="sup_confirm_create")],
            [InlineKeyboardButton("✏️ Editar", callback_data="sup_edit_menu")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="sup_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        progress = get_progress_bar(6)

        # Limita descrição a 200 caracteres para exibição
        description = state['description']
        desc_preview = description[:200] + ("..." if len(description) > 200 else "")

        message = (
            f"🎮 **SUPORTE GAMER ONCABO**\n\n"
            f"{progress} - **Confirmação Final**\n\n"
            f"🎯 **Pronto! Vamos revisar juntos antes de finalizar?**\n\n"
            f"📋 **Resumo do seu chamado:**\n\n"
            f"🔸 **Categoria:** {state['category_name']}\n"
            f"🔸 **Jogo:** {state['game_name']}\n"
            f"🔸 **Quando começou:** {state['timing_name']}\n"
            f"🔸 **Anexos:** {attachments_count} arquivo(s)\n\n"
            f"📝 **Descrição:**\n{desc_preview}\n\n"
            f"💡 Dá uma olhada se está tudo certo. Se quiser mudar algo, é só clicar em \"Editar\"!\n\n"
            f"✅ **Tudo certo?** Então pode confirmar! Vou encaminhar para nossa equipe técnica "
            f"imediatamente e você terá retorno em até **24h úteis!** 🚀"
        )

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _handle_support_confirmation(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa confirmação de criação do ticket."""
        if callback_data == "sup_confirm_create":
            await self._create_ticket_from_support_flow(query, context)

    async def _handle_support_edit(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa edição de campos."""
        if callback_data == "sup_edit_menu":
            # Mostra menu de edição
            keyboard = [
                [InlineKeyboardButton("📁 Editar Categoria", callback_data="sup_edit_category")],
                [InlineKeyboardButton("🎮 Editar Jogo", callback_data="sup_edit_game")],
                [InlineKeyboardButton("📅 Editar Quando Começou", callback_data="sup_edit_timing")],
                [InlineKeyboardButton("📝 Editar Descrição", callback_data="sup_edit_description")],
                [InlineKeyboardButton("📎 Editar Anexos", callback_data="sup_edit_attachments")],
                [InlineKeyboardButton("◀️ Voltar", callback_data="sup_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "✏️ **O que deseja editar?**\n\nSelecione o campo que deseja alterar:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif callback_data == "sup_edit_category":
            state = get_support_state(context)
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1
            await self._show_category_step(query, context)
        elif callback_data == "sup_edit_game":
            state = get_support_state(context)
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self._show_game_step(query, context)
        elif callback_data == "sup_edit_timing":
            state = get_support_state(context)
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self._show_timing_step(query, context)
        elif callback_data == "sup_edit_description":
            state = get_support_state(context)
            state['state'] = SupportState.DESCRIPTION
            state['current_step'] = 4

            await query.edit_message_text(
                "📝 Digite a nova descrição do problema:",
                parse_mode='Markdown'
            )
        elif callback_data == "sup_edit_attachments":
            state = get_support_state(context)
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5
            await self._show_attachments_step(query, context)

    async def _create_ticket_from_support_flow(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Cria ticket a partir do fluxo de suporte, usando a nova arquitetura
        e o endpoint correto do HubSoft.
        """
        state = get_support_state(context)
        user = query.from_user

        try:
            await query.edit_message_text(
                "⏳ **Criando seu chamado...**\n\n"
                "Aguarde enquanto registro suas informações no sistema.",
                parse_mode='Markdown'
            )

            # 1. Montar a descrição enriquecida
            user_mention = f"@{user.username}" if user.username else f"ID: {user.id}"
            now_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
            
            enhanced_description = (
                f"-- ABERTO VIA BOT TELEGRAM --\n"
                f"Data/Hora: {now_str}\n"
                f"Usuário: {user_mention}\n"
                f"---------------------------\n"
                f"{state['description']}"
            )

            # 2. Montar os dados do ticket
            ticket_data = {
                "user_id": user.id,
                "user_name": user.first_name,
                "user_telegram": user_mention,
                "category": state['category'],
                "game_name": state['game_name'],
                "timing": state['timing_name'],
                "description": enhanced_description,
                "attachments": state.get('attachments', [])
            }

            # 3. Chamar o Use Case correto
            logger.info(f"Iniciando criação de ticket para usuário {user.id} via Use Case...")
            hubsoft_result = await self._hubsoft_use_case.create_support_ticket(ticket_data)

            if not hubsoft_result.success:
                error_message = (
                    "❌ **Não foi possível criar seu chamado**\n\n"
                    "Nosso sistema de suporte está temporariamente indisponível.\n\n"
                    f"**Código do erro:** {hubsoft_result.error_code or 'CREATE_TICKET_ERROR'}\n\n"
                    "Por favor, tente novamente em alguns minutos."
                )
                await query.edit_message_text(error_message, parse_mode='Markdown')
                logger.error(f"Falha ao criar ticket para usuário {user.id}: {hubsoft_result.message}")
                return

            # 4. Montar mensagem de sucesso com o protocolo real
            hubsoft_protocol = hubsoft_result.data.get("protocolo") or f"ID {hubsoft_result.data.get('id_atendimento')}"
            now = datetime.now()
            
            success_message = (
                f"🎉 **PRONTO! SEU CHAMADO FOI CRIADO COM SUCESSO!**\n\n"
                f"📋 **Protocolo:** `{hubsoft_protocol}`\n"
                f"📅 **Criado em:** {now.strftime('%d/%m/%Y às %H:%M')}\n"
                f"📊 **Status:** Aguardando Atendimento\n\n"
                f"✅ Nossa equipe técnica já recebeu seu chamado e vai começar a análise.\n\n"
                f"Você receberá todas as atualizações aqui pelo Telegram. "
                f"O tempo médio de primeira resposta é de **até 24h úteis**.\n\n"
                f"Obrigado pela paciência! 🙏"
            )
            await query.edit_message_text(success_message, parse_mode='Markdown')

            # 5. Notificar a equipe
            try:
                notification_desc = state['description'][:200] + '...' if len(state['description']) > 200 else state['description']
                notification = (
                    f"🎫 **NOVO CHAMADO - VIA BOT**\n\n"
                    f"📋 **Protocolo:** `{hubsoft_protocol}`\n"
                    f"👤 **Cliente:** {user_mention}\n"
                    f"🎯 **Categoria:** {state['category_name']}\n"
                    f"🎮 **Jogo:** {state['game_name']}\n"
                    f"📝 **Descrição:**\n{notification_desc}"
                )
                await context.bot.send_message(
                    chat_id=int(TELEGRAM_GROUP_ID),
                    message_thread_id=int(SUPPORT_TOPIC_ID),
                    text=notification,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Erro ao enviar notificação de novo ticket ao grupo: {e}")

            clear_support_state(context)
            logger.info(f"Ticket {hubsoft_protocol} criado com sucesso para usuário {user.id}")

        except Exception as e:
            logger.error(f"Erro crítico ao criar ticket: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ **Erro ao criar chamado**\n\n"
                "Ocorreu um erro inesperado. Por favor, tente novamente com /suporte.",
                parse_mode='Markdown'
            )

    async def _is_admin(self, user_id: int) -> bool:
        """Verifica se usuário é administrador consultando o repositório."""
        # Garante que o repositório está inicializado
        if not self._admin_repo:
            await self._ensure_initialized()
        
        return await self._admin_repo.is_administrator(user_id)

    def _get_status_emoji(self, status: str) -> str:
        """Retorna emoji correspondente ao status do atendimento."""
        status_emojis = {
            "pending": "⏳",
            "open": "🔵",
            "in_progress": "🔄",
            "resolved": "✅",
            "closed": "🔒",
            "cancelled": "❌"
        }
        return status_emojis.get(status, "❓")

    def _get_status_name_pt(self, status: str) -> str:
        """Retorna nome do status em português amigável."""
        status_names = {
            "pending": "Aguardando Atendimento",
            "open": "Em Análise",
            "in_progress": "Em Atendimento",
            "resolved": "Resolvido",
            "closed": "Fechado",
            "cancelled": "Cancelado"
        }
        return status_names.get(status, status.title())

    async def handle_new_member(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa entrada de novos membros no grupo."""
        try:
            await self._ensure_initialized()

            # Pega informações do chat member update
            if not update.chat_member:
                return

            new_member = update.chat_member.new_chat_member
            old_member = update.chat_member.old_chat_member
            user = update.chat_member.from_user
            chat = update.effective_chat

            # Verifica se é um novo membro (não estava no grupo antes)
            if old_member.status in ['left', 'kicked'] and new_member.status == 'member':
                logger.info(f"Novo membro detectado: {user.first_name} ({user.id})")

                # Usa WelcomeManagementUseCase se disponível
                if hasattr(self, '_welcome_use_case') and self._welcome_use_case:
                    from ...domain.value_objects.welcome_message import WelcomeMessage
                    from ...core.config import WELCOME_TOPIC_ID, RULES_TOPIC_ID
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                    # Cria mensagem de boas-vindas
                    welcome_msg = WelcomeMessage.create_initial_welcome(
                        welcome_topic_id=int(WELCOME_TOPIC_ID) if WELCOME_TOPIC_ID else None
                    )

                    # Formata menção HTML
                    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
                    welcome_text = welcome_msg.format_for_user(
                        user_mention=user_mention,
                        username=user.first_name
                    )

                    # Envia mensagem de boas-vindas no tópico correto
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=welcome_text,
                        parse_mode='HTML',
                        message_thread_id=int(WELCOME_TOPIC_ID) if WELCOME_TOPIC_ID else None
                    )

                    # Envia mensagem de regras com botão
                    if RULES_TOPIC_ID:
                        rules_msg = WelcomeMessage.create_rules_reminder(
                            rules_topic_id=int(RULES_TOPIC_ID),
                            user_id=user.id
                        )

                        rules_text = rules_msg.format_for_user(
                            user_mention=user_mention,
                            username=user.first_name
                        )

                        # Cria botão inline
                        keyboard = [[
                            InlineKeyboardButton(
                                rules_msg.button_text,
                                callback_data=rules_msg.button_callback
                            )
                        ]]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await context.bot.send_message(
                            chat_id=chat.id,
                            text=rules_text,
                            parse_mode='HTML',
                            message_thread_id=int(RULES_TOPIC_ID),
                            reply_markup=reply_markup
                        )

                    # Registra no use case
                    result = await self._welcome_use_case.handle_new_member(
                        user_id=user.id,
                        username=user.username or user.first_name,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )

                    if result.success:
                        logger.info(f"Novo membro {user.first_name} processado com sucesso")
                    else:
                        logger.error(f"Erro ao processar novo membro: {result.message}")

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