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

from ...infrastructure.config.container import get_container
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

    async def _ensure_initialized(self) -> None:
        """Garante que o handler está inicializado."""
        if self._container is None:
            self._container = await get_container()
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")
            self._cpf_use_case = self._container.get("cpf_verification_use_case")
            self._admin_use_case = self._container.get("admin_operations_use_case")

    async def handle_start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /start."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            welcome_message = (
                f"🎮 Olá {user.first_name}! Bem-vindo ao suporte OnCabo Gaming!\n\n"
                "🔧 Para criar um ticket de suporte, use /suporte\n"
                "📋 Para verificar seus tickets, use /status\n"
                "🆔 Para verificar seu CPF, use /verificar_cpf\n\n"
                "💡 Digite /ajuda para ver todos os comandos disponíveis."
            )

            await update.message.reply_text(welcome_message)

            logger.info(f"Usuário {user.id} iniciou conversa")

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
            except:
                pass

    async def _get_tickets_from_old_table(self, user_id: int) -> list:
        """
        TEMPORÁRIO: Busca tickets da tabela antiga support_tickets.
        TODO: Migrar dados para nova tabela e remover este método.
        """
        import aiosqlite
        from ...core.config import DATABASE_FILE

        tickets = []
        try:
            async with aiosqlite.connect(DATABASE_FILE) as db:
                async with db.execute(
                    """
                    SELECT id, category, affected_game, problem_started,
                           description, status, created_at, updated_at,
                           hubsoft_protocol, urgency_level
                    FROM support_tickets
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        tickets.append({
                            'id': row[0],
                            'category': row[1],
                            'affected_game': row[2],
                            'problem_timing': row[3],
                            'description': row[4],
                            'status': row[5],
                            'created_at': row[6],
                            'updated_at': row[7],
                            'protocol': row[8],
                            'urgency': row[9]
                        })
        except Exception as e:
            logger.error(f"Erro ao buscar tickets da tabela antiga: {e}")

        return tickets

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

            # TEMPORÁRIO: Busca da tabela antiga até migração completa
            tickets = await self._get_tickets_from_old_table(user.id)

            if not tickets:
                # Usuário não tem nenhum ticket
                message = (
                    "📋 **Seus Tickets de Suporte**\n\n"
                    "👋 Olá! Você ainda não tem nenhum ticket de suporte aberto.\n\n"
                    "💡 **Precisa de ajuda?**\n"
                    "Use o comando /suporte para abrir um novo chamado!\n\n"
                    "Nossa equipe está sempre pronta para te ajudar! 😊"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                logger.info(f"Usuário {user.id} verificou status - sem tickets")
                return

            # Separa tickets ativos e finalizados
            active_statuses = ['pending', 'open', 'in_progress']
            active_tickets = [t for t in tickets if t['status'] in active_statuses]
            finished_tickets = [t for t in tickets if t['status'] not in active_statuses]

            # Monta mensagem com lista de tickets
            message_parts = ["📋 **Seus Tickets de Suporte**\n"]

            # Resumo geral
            total = len(tickets)
            active_count = len(active_tickets)
            finished_count = len(finished_tickets)

            message_parts.append(
                f"📊 **Resumo:** {total} ticket(s) no total\n"
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

            # Lista tickets ativos
            if active_tickets:
                message_parts.append("\n🔴 **TICKETS ATIVOS**\n")
                for ticket in active_tickets:
                    status_emoji = self._get_status_emoji(ticket['status'])
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
                        f"   📅 Aberto há {days_open} dia(s)\n"
                    )

                    if ticket.get('affected_game'):
                        message_parts.append(f"   🎮 {ticket['affected_game']}\n")

            # Lista últimos 3 tickets finalizados
            if finished_tickets:
                message_parts.append("\n✅ **ÚLTIMOS TICKETS FINALIZADOS**\n")
                recent_finished = finished_tickets[:3]

                for ticket in recent_finished:
                    status_emoji = self._get_status_emoji(ticket['status'])
                    protocol = ticket.get('protocol') or f"#{ticket['id']:06d}"
                    category = category_names.get(ticket['category'], ticket['category'])

                    message_parts.append(
                        f"\n{status_emoji} **{protocol}**\n"
                        f"   📂 {category}\n"
                        f"   🏁 Status: {ticket['status'].title()}\n"
                    )

                if len(finished_tickets) > 3:
                    message_parts.append(f"\n_... e mais {len(finished_tickets) - 3} finalizado(s)_\n")

            # Rodapé com dicas
            message_parts.append(
                "\n💡 **Dicas:**\n"
                "• Use /suporte para abrir novo chamado\n"
                "• Nossa equipe trabalha 24/7 para te atender!\n\n"
                "🙏 Agradecemos sua paciência e confiança!"
            )

            message = "".join(message_parts)

            # Cria botões inline para ações rápidas
            keyboard = []

            if active_tickets:
                keyboard.append([
                    InlineKeyboardButton(
                        "🆕 Abrir Novo Ticket",
                        callback_data="status_new_ticket"
                    )
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(
                        "🆘 Preciso de Ajuda",
                        callback_data="status_new_ticket"
                    )
                ])

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
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

    async def handle_verify_cpf_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Processa comando /verificar_cpf."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            if not user:
                return

            # Verifica se já tem verificação pendente
            pending_verification = await self._cpf_use_case.get_pending_verification(user.id)

            if pending_verification.success and pending_verification.data:
                message = (
                    "⏳ **Verificação Pendente**\n\n"
                    "Você já tem uma verificação de CPF em andamento.\n\n"
                    "📱 Por favor, responda com seu CPF para continuar."
                )
            else:
                # Inicia nova verificação
                result = await self._cpf_use_case.start_verification(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    verification_type="hubsoft_sync"
                )

                if result.success:
                    message = (
                        "🆔 **Verificação de CPF**\n\n"
                        "Para verificar seu cadastro no sistema, preciso validar seu CPF.\n\n"
                        "📱 **Digite seu CPF** (apenas números):\n"
                        "Exemplo: 12345678901\n\n"
                        "🔒 Seus dados estão protegidos e serão usados apenas para verificação."
                    )
                else:
                    message = f"❌ Erro ao iniciar verificação: {result.message}"

            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} iniciou verificação de CPF")

        except Exception as e:
            logger.error(f"Erro no comando /verificar_cpf: {e}")
            await update.message.reply_text(
                "❌ Erro ao iniciar verificação. Tente novamente."
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
            if not self._is_admin(user.id):
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

            # Callbacks do novo fluxo de suporte
            if callback_data.startswith("sup_"):
                await self._handle_support_callback(query, context, callback_data)
            # Callbacks do comando /status
            elif callback_data == "status_new_ticket":
                await self._handle_status_new_ticket(query, context)
            # Callbacks antigos (manter compatibilidade)
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

        if not self._is_admin(user.id):
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

            # Verifica se está em fluxo de suporte
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

            # Verifica se é CPF (apenas números)
            if text and text.isdigit() and len(text) == 11:
                await self._handle_cpf_input(update, text)
                return

            # Outras mensagens de texto
            message = (
                "💬 Mensagem recebida!\n\n"
                "Para criar um ticket de suporte, use /suporte\n"
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
                    "Para criar um ticket de suporte com anexos, use /suporte",
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

    async def _handle_cpf_input(self, update: Update, cpf: str) -> None:
        """Processa entrada de CPF."""
        user = update.effective_user

        try:
            # Processa verificação via use case
            result = await self._cpf_use_case.process_verification_with_cpf(
                user_id=user.id,
                cpf_number=cpf
            )

            if result.success:
                if result.data and result.data.get('verified'):
                    client_data = result.data.get('client_data', {})
                    client_name = client_data.get('name', 'Cliente')

                    message = (
                        f"✅ **CPF Verificado com Sucesso!**\n\n"
                        f"👤 **Nome:** {client_name}\n"
                        f"📋 **CPF:** {cpf[:3]}***{cpf[-2:]}\n\n"
                        "🎮 Agora você pode criar tickets de suporte!"
                    )
                else:
                    message = (
                        "❌ **CPF não encontrado no sistema**\n\n"
                        "Seu CPF não foi localizado em nossa base de dados.\n\n"
                        "📞 Entre em contato conosco para mais informações."
                    )
            else:
                message = f"❌ Erro na verificação: {result.message}"

            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro ao processar CPF: {e}")
            await update.message.reply_text(
                "❌ Erro ao verificar CPF. Tente novamente."
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
        """Cria ticket a partir do fluxo de suporte."""
        state = get_support_state(context)
        user = query.from_user

        try:
            # Gera protocolo
            now = datetime.now()
            protocol = f"TKT-{now.strftime('%Y%m%d')}-{user.id % 10000:04d}"

            # Mensagem de sucesso
            success_message = (
                f"🎉 **PRONTO! SEU CHAMADO FOI CRIADO COM SUCESSO!**\n\n"
                f"📋 **Protocolo:** `{protocol}`\n"
                f"📅 **Criado em:** {now.strftime('%d/%m/%Y às %H:%M')}\n"
                f"📊 **Status:** Aguardando Atendimento\n\n"
                f"✅ Nossa equipe técnica já recebeu todas as informações e vai começar a "
                f"trabalhar no seu caso o quanto antes! 💪\n\n"
                f"📱 **Fique tranquilo:**\n"
                f"• Você receberá todas as atualizações aqui mesmo pelo Telegram\n"
                f"• Tempo médio de resposta: **até 24h úteis**\n"
                f"• Nossa meta: resolver seu problema o mais rápido possível!\n\n"
                f"💬 Enquanto isso, se lembrar de mais algum detalhe importante, pode me "
                f"mandar que eu adiciono ao seu chamado! 😊\n\n"
                f"🔍 **Seu protocolo:** `{protocol}` _(guarde para consultas)_\n\n"
                f"📣 Acompanhe as respostas no grupo, tópico **Suporte Gamer**!"
            )

            await query.edit_message_text(
                success_message,
                parse_mode='Markdown'
            )

            # Envia notificação ao tópico do grupo
            try:
                notification = (
                    f"🎫 **NOVO CHAMADO - Atenção Equipe!**\n\n"
                    f"📋 **Protocolo:** `{protocol}`\n"
                    f"👤 **Cliente:** @{user.username or user.first_name}\n"
                    f"🎯 **Categoria:** {state['category_name']}\n"
                    f"🎮 **Jogo:** {state['game_name']}\n"
                    f"⏰ **Quando começou:** {state['timing_name']}\n"
                    f"📎 **Anexos:** {len(state.get('attachments', []))} arquivo(s)\n\n"
                    f"✅ Cliente já foi informado - aguardando nossa análise!\n"
                    f"🔔 **Prazo de resposta:** 24h úteis"
                )

                await context.bot.send_message(
                    chat_id=int(TELEGRAM_GROUP_ID),
                    message_thread_id=int(SUPPORT_TOPIC_ID),
                    text=notification,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Erro ao enviar notificação de ticket ao grupo: {e}")

            # Limpa estado
            clear_support_state(context)

            logger.info(f"Ticket {protocol} criado para usuário {user.id}")

        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            await query.edit_message_text(
                "❌ Erro ao criar chamado. Por favor, tente novamente com /suporte",
                parse_mode='Markdown'
            )

    def _is_admin(self, user_id: int) -> bool:
        """Verifica se usuário é administrador."""
        # TODO: Implementar verificação real de admin
        admin_list = [123456789, 987654321]  # IDs de exemplo
        return user_id in admin_list

    def _get_status_emoji(self, status: str) -> str:
        """Retorna emoji correspondente ao status do ticket."""
        status_emojis = {
            "pending": "⏳",
            "open": "🔵",
            "in_progress": "🔄",
            "resolved": "✅",
            "closed": "🔒",
            "cancelled": "❌"
        }
        return status_emojis.get(status, "❓")

    async def _handle_status_new_ticket(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Callback: Abrir novo ticket a partir do /status."""
        try:
            user = query.from_user

            # Edita mensagem original
            await query.edit_message_text(
                "🆕 **Vamos abrir um novo chamado!**\n\n"
                "Redirecionando você para o formulário de suporte...",
                parse_mode='Markdown'
            )

            # Inicializa novo fluxo de suporte
            init_support_state(context)
            state = get_support_state(context)
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1

            # Envia mensagem de início do suporte (igual ao /suporte)
            progress_bar = self._create_progress_bar(1, 6)

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

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"{progress_bar}\n\n"
                    "🎯 **Passo 1/6: Categoria do Problema**\n\n"
                    "Olá! Fico feliz em te ajudar! 😊\n\n"
                    "Primeiro, me diz qual o tipo do seu problema:\n\n"
                    "Escolha a categoria que mais se encaixa:"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} iniciou novo ticket via callback /status")

        except Exception as e:
            logger.error(f"Erro no callback status_new_ticket: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Erro ao iniciar novo ticket.\n\n"
                "Por favor, use o comando /suporte para tentar novamente."
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