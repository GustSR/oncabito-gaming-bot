"""
Support Form Handler.

Handler especializado para fluxos conversacionais de suporte,
incluindo categorização, coleta de informações e criação de tickets.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
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


class SupportFormHandler:
    """Handler para gerenciar o fluxo conversacional de suporte."""

    def __init__(self, container):
        """
        Inicializa o handler de formulário de suporte.

        Args:
            container: DI Container com dependências.
        """
        self._container = container
        self._hubsoft_use_case: HubSoftIntegrationUseCase = None

    def _ensure_hubsoft_use_case(self) -> HubSoftIntegrationUseCase:
        """Garante que o HubSoft use case está inicializado."""
        if self._hubsoft_use_case is None:
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")
        return self._hubsoft_use_case

    async def handle_support_callback(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Router principal para callbacks do fluxo de suporte."""
        # Cancel
        if callback_data == "sup_cancel":
            await self.handle_support_cancel(query, context)
        # Back
        elif callback_data == "sup_back":
            await self.handle_support_back(query, context)
        # Category selection
        elif callback_data.startswith("sup_cat_"):
            await self.handle_support_category(query, context, callback_data)
        # Game selection
        elif callback_data.startswith("sup_game_"):
            await self.handle_support_game(query, context, callback_data)
        # Timing selection
        elif callback_data.startswith("sup_timing_"):
            await self.handle_support_timing(query, context, callback_data)
        # Attachments
        elif callback_data.startswith("sup_att_"):
            await self.handle_support_attachment_action(query, context, callback_data)
        # Confirmation
        elif callback_data.startswith("sup_confirm_"):
            await self.handle_support_confirmation(query, context, callback_data)
        # Edit
        elif callback_data.startswith("sup_edit_"):
            await self.handle_support_edit(query, context, callback_data)
        else:
            logger.warning(f"Callback de suporte não reconhecido: {callback_data}")

    async def handle_support_cancel(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cancela o fluxo de suporte."""
        clear_support_state(context)
        await query.edit_message_text(
            "❌ **Formulário Cancelado**\n\n"
            "Você pode iniciar um novo chamado a qualquer momento usando /suporte",
            parse_mode='Markdown'
        )
        logger.info(f"Usuário {query.from_user.id} cancelou o fluxo de suporte")

    async def handle_support_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Volta para etapa anterior."""
        state = get_support_state(context)
        current_state = state['state']

        # Define para onde voltar
        if current_state == SupportState.GAME:
            # Volta para categoria
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1
            await self.show_category_step(query, context)
        elif current_state == SupportState.TIMING:
            # Volta para jogo
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self.show_game_step(query, context)
        elif current_state == SupportState.ATTACHMENTS:
            # Volta para timing
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self.show_timing_step(query, context)
        elif current_state == SupportState.CONFIRMATION:
            # Volta para attachments
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5
            await self.show_attachments_step(query, context)
        else:
            await query.answer("Não é possível voltar nesta etapa")

    async def handle_support_category(
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

        await self.show_game_step(query, context)
        logger.info(f"Usuário {query.from_user.id} selecionou categoria: {category_key}")

    async def show_game_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def show_category_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def handle_support_game(
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

        await self.show_timing_step(query, context)
        logger.info(f"Usuário {query.from_user.id} selecionou jogo: {game_key}")

    async def show_timing_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def handle_support_timing(
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

    async def show_attachments_step(self, query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def handle_support_attachment_action(
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
            await self.show_confirmation_step(query, context)

    async def show_confirmation_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    async def handle_support_confirmation(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa confirmação de criação do ticket."""
        if callback_data == "sup_confirm_create":
            await self.create_ticket_from_support_flow(query, context)

    async def handle_support_edit(
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
            await self.show_category_step(query, context)
        elif callback_data == "sup_edit_game":
            state = get_support_state(context)
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self.show_game_step(query, context)
        elif callback_data == "sup_edit_timing":
            state = get_support_state(context)
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self.show_timing_step(query, context)
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
            await self.show_attachments_step(query, context)

    async def create_ticket_from_support_flow(
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
            hubsoft_use_case = self._ensure_hubsoft_use_case()
            hubsoft_result = await hubsoft_use_case.create_support_ticket(ticket_data)

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

    async def handle_description_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str
    ) -> bool:
        """
        Processa entrada de descrição no fluxo de suporte.

        Returns:
            bool: True se a mensagem foi processada, False caso contrário.
        """
        # Verifica se está em fluxo de suporte (usuário verificado)
        if 'support' not in context.user_data:
            return False

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
                return True

            # Salva descrição
            state['description'] = text.strip()
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5

            # Mostra etapa de anexos
            await self.show_attachments_step(update.message, context)
            logger.info(f"Usuário {update.effective_user.id} enviou descrição ({len(text)} chars)")
            return True

        return False

    async def handle_photo_attachment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Processa fotos como anexos no fluxo de suporte.

        Returns:
            bool: True se a foto foi processada, False caso contrário.
        """
        user = update.effective_user

        # Verifica se está em fluxo de suporte e aguardando anexos
        if 'support' not in context.user_data:
            return False

        state = get_support_state(context)

        # Só aceita fotos na etapa de anexos
        if state['state'] != SupportState.ATTACHMENTS:
            return False

        # Verifica limite de anexos
        attachments = state.get('attachments', [])
        if len(attachments) >= 3:
            await update.message.reply_text(
                "❌ Limite de 3 anexos atingido!\n\n"
                "Clique em **Continuar** para prosseguir.",
                parse_mode='Markdown'
            )
            return True

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
        return True
