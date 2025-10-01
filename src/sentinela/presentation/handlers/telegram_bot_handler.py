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
                            f"✅ @{user.username or user.first_name}, recebi seu pedido de suporte!\n\n"
                            f"Vou te chamar no privado agora para coletar as informações do seu problema "
                            f"de forma organizada.\n\n"
                            f"Por favor, verifique suas mensagens diretas comigo! 👆"
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
                f"Vamos criar seu chamado de suporte de forma rápida e organizada!\n\n"
                f"{progress} - Categoria do Problema\n\n"
                f"Selecione a categoria que melhor descreve seu problema:"
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

            # Busca tickets do usuário via use case
            user_id = UserId(user.id)

            # Por enquanto, simulamos a resposta até a migração completa
            # TODO: Implementar busca real de tickets
            message = (
                "📋 **Seus Tickets de Suporte**\n\n"
                "🔄 Buscando seus tickets...\n\n"
                "⚠️ Sistema em migração - funcionalidade será restaurada em breve."
            )

            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} verificou status dos tickets")

        except Exception as e:
            logger.error(f"Erro no comando /status: {e}")
            await update.message.reply_text(
                "❌ Erro ao buscar tickets. Tente novamente."
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
                            "❌ A descrição precisa ter pelo menos 10 caracteres.\n\n"
                            "Por favor, descreva o problema com mais detalhes.",
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
            await update.message.reply_text(
                f"✅ **Anexo {attachments_count}/3 adicionado com sucesso!**\n\n"
                f"📸 Você pode enviar mais {3 - attachments_count} foto(s) ou clicar em **Continuar**.",
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
            f"{progress} - Jogo Afetado\n\n"
            f"Qual jogo está com problema?"
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
            f"{progress} - Quando Começou?\n\n"
            f"Quando você percebeu esse problema pela primeira vez?"
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
            f"{progress} - Detalhes do Problema\n\n"
            f"📝 Agora me conte com detalhes sobre o problema:\n\n"
            f"💡 **Dicas do que incluir:**\n"
            f"• O que exatamente está acontecendo?\n"
            f"• Qual é o sintoma (lag, ping alto, desconexões)?\n"
            f"• Em qual servidor/região você joga?\n"
            f"• Já tentou reiniciar o roteador?\n"
            f"• Outros dispositivos têm o mesmo problema?\n\n"
            f"✍️ **Digite sua mensagem** explicando o problema em detalhes:"
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
            f"{progress} - Anexos (Opcional)\n\n"
            f"📎 **Você pode enviar até 3 imagens:**\n"
            f"• Screenshot do ping in-game\n"
            f"• Foto do resultado de teste de velocidade\n"
            f"• Print de tela com erro\n\n"
            f"Anexos enviados: **{attachments_count}/3**\n\n"
            f"📷 Envie suas fotos agora ou clique em **Pular Anexos** para continuar."
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
            f"{progress} - Confirmação\n\n"
            f"📋 **RESUMO DO SEU CHAMADO:**\n\n"
            f"🔸 **Categoria:** {state['category_name']}\n"
            f"🔸 **Jogo:** {state['game_name']}\n"
            f"🔸 **Quando começou:** {state['timing_name']}\n"
            f"🔸 **Anexos:** {attachments_count} arquivo(s)\n\n"
            f"📝 **Descrição:**\n{desc_preview}\n\n"
            f"✅ Está tudo correto? **Confirma a criação do chamado?**"
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
                f"🎉 **CHAMADO CRIADO COM SUCESSO!**\n\n"
                f"📋 **Protocolo:** `{protocol}`\n"
                f"📅 **Criado em:** {now.strftime('%d/%m/%Y às %H:%M')}\n"
                f"📊 **Status:** Aguardando Atendimento\n\n"
                f"✅ **Seu chamado foi registrado e nossa equipe técnica já foi notificada!**\n\n"
                f"📞 **Próximos passos:**\n"
                f"• Você receberá atualizações aqui no Telegram\n"
                f"• Tempo de resposta: até 24h úteis\n"
                f"• Mantenha o protocolo para acompanhamento\n\n"
                f"🔍 **Protocolo para consulta:** `{protocol}`\n\n"
                f"💬 Acompanhe as respostas no grupo, tópico **Suporte Gamer**!"
            )

            await query.edit_message_text(
                success_message,
                parse_mode='Markdown'
            )

            # Envia notificação ao tópico do grupo
            try:
                notification = (
                    f"🎫 **NOVO CHAMADO ABERTO**\n\n"
                    f"📋 **Protocolo:** `{protocol}`\n"
                    f"👤 **Cliente:** @{user.username or user.first_name}\n"
                    f"🔸 **Categoria:** {state['category_name']}\n"
                    f"🎮 **Jogo:** {state['game_name']}\n\n"
                    f"Nossa equipe técnica já está analisando! 🔧"
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