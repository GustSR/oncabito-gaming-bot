"""
Support Form Handler.

Handler especializado para fluxos conversacionais de suporte,
incluindo categorização, coleta de informações e criação de tickets.

NOVO: Sistema de persistência de sessões - o progresso do formulário
é salvo no banco de dados, permitindo que usuários retomem o preenchimento
mesmo após reinicializações do bot.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
from ...domain.repositories.support_session_repository import SupportSessionRepository
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
        self._support_session_repository: SupportSessionRepository = None

    def _ensure_hubsoft_use_case(self) -> HubSoftIntegrationUseCase:
        """Garante que o HubSoft use case está inicializado."""
        if self._hubsoft_use_case is None:
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")
        return self._hubsoft_use_case

    def _ensure_support_session_repository(self) -> SupportSessionRepository:
        """Garante que o repositório de sessões está inicializado."""
        if self._support_session_repository is None:
            self._support_session_repository = self._container.get("support_session_repository")
        return self._support_session_repository

    def _create_initial_state(self) -> Dict[str, Any]:
        """
        Cria estrutura inicial do estado de suporte.

        Returns:
            Dict com estado limpo do formulário
        """
        return {
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

    async def _get_support_state(self, user_id: int) -> Dict[str, Any]:
        """
        Obtém estado do suporte para o usuário do banco de dados.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            Dict[str, Any]: Estado do formulário (cria novo se não existir)
        """
        repository = self._ensure_support_session_repository()
        session_data = await repository.find_session(user_id)

        if session_data:
            # Retorna o estado deserializado do banco
            return session_data['state_json']

        # Se não existe, cria um novo estado
        return self._create_initial_state()

    async def _save_support_state(self, user_id: int, state: Dict[str, Any]) -> bool:
        """
        Salva estado do suporte no banco de dados.

        Args:
            user_id: ID do Telegram do usuário
            state: Estado completo do formulário

        Returns:
            bool: True se salvou com sucesso
        """
        repository = self._ensure_support_session_repository()
        current_step = state.get('state', SupportState.IDLE)

        success = await repository.save_session(
            user_id=user_id,
            state_json=state,
            current_step=current_step
        )

        if success:
            logger.debug(f"Estado de suporte salvo para usuário {user_id} (passo: {current_step})")
        else:
            logger.error(f"Falha ao salvar estado de suporte para usuário {user_id}")

        return success

    async def _clear_support_state(self, user_id: int) -> bool:
        """
        Remove estado do suporte do banco de dados.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            bool: True se removeu com sucesso
        """
        repository = self._ensure_support_session_repository()
        success = await repository.delete_session(user_id)

        if success:
            logger.debug(f"Estado de suporte limpo para usuário {user_id}")

        return success

    async def start_support_flow(self, user_id: int) -> bool:
        """
        Inicia uma nova sessão de suporte para o usuário.

        Cria um estado inicial e salva no banco de dados.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            bool: True se iniciou com sucesso
        """
        state = self._create_initial_state()
        state['state'] = SupportState.CATEGORY
        state['current_step'] = 1

        success = await self._save_support_state(user_id, state)

        if success:
            logger.info(f"Fluxo de suporte iniciado para usuário {user_id}")
        else:
            logger.error(f"Falha ao iniciar fluxo de suporte para usuário {user_id}")

        return success

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
        await self._clear_support_state(query.from_user.id)
        await query.edit_message_text(
            "❌ **Formulário Cancelado**\n\n"
            "Você pode iniciar um novo chamado a qualquer momento usando /suporte",
            parse_mode='Markdown'
        )
        logger.info(f"Usuário {query.from_user.id} cancelou o fluxo de suporte")

    async def handle_support_back(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Volta para etapa anterior."""
        user_id = query.from_user.id
        state = await self._get_support_state(user_id)
        current_state = state['state']

        # Define para onde voltar
        if current_state == SupportState.GAME:
            # Volta para categoria
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1
            await self._save_support_state(user_id, state)
            await self.show_category_step(query, context)
        elif current_state == SupportState.TIMING:
            # Volta para jogo
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self._save_support_state(user_id, state)
            await self.show_game_step(query, context)
        elif current_state == SupportState.ATTACHMENTS:
            # Volta para timing
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self._save_support_state(user_id, state)
            await self.show_timing_step(query, context)
        elif current_state == SupportState.CONFIRMATION:
            # Volta para attachments
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5
            await self._save_support_state(user_id, state)
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
        user_id = query.from_user.id
        category_key = callback_data.replace("sup_cat_", "")

        category_names = {
            "connectivity": "🌐 Conectividade/Ping",
            "performance": "⚡ Performance/FPS",
            "game_issues": "🎮 Problemas no Jogo",
            "configuration": "💻 Configuração",
            "others": "📞 Outros"
        }

        state = await self._get_support_state(user_id)
        state['category'] = category_key
        state['category_name'] = category_names.get(category_key, "Outros")
        state['state'] = SupportState.GAME
        state['current_step'] = 2

        await self._save_support_state(user_id, state)
        await self.show_game_step(query, context)
        logger.info(f"Usuário {user_id} selecionou categoria: {category_key}")

    async def show_game_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de jogo."""
        user_id = query.from_user.id
        state = await self._get_support_state(user_id)

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
        user_id = query.from_user.id
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

        state = await self._get_support_state(user_id)
        state['game'] = game_key
        state['game_name'] = game_names.get(game_key, "Outro")
        state['state'] = SupportState.TIMING
        state['current_step'] = 3

        await self._save_support_state(user_id, state)
        await self.show_timing_step(query, context)
        logger.info(f"Usuário {user_id} selecionou jogo: {game_key}")

    async def show_timing_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de seleção de timing."""
        user_id = query.from_user.id
        state = await self._get_support_state(user_id)

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
        user_id = query.from_user.id
        timing_key = callback_data.replace("sup_timing_", "")

        timing_names = {
            "now": "🔴 Agora/Hoje",
            "yesterday": "📅 Ontem",
            "week": "📆 Esta Semana",
            "lastweek": "🗓️ Semana Passada",
            "longtime": "⏰ Há Muito Tempo",
            "always": "♾️ Sempre Foi Assim"
        }

        state = await self._get_support_state(user_id)
        state['timing'] = timing_key
        state['timing_name'] = timing_names.get(timing_key, "Não informado")
        state['state'] = SupportState.DESCRIPTION
        state['current_step'] = 4

        await self._save_support_state(user_id, state)

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

        logger.info(f"Usuário {user_id} selecionou timing: {timing_key}")

    async def show_attachments_step(self, query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de anexos opcionais."""
        # Extrai user_id dependendo se é query ou message
        if hasattr(query_or_message, 'from_user'):
            user_id = query_or_message.from_user.id
        else:
            user_id = query_or_message.message.from_user.id if hasattr(query_or_message, 'message') else query_or_message.chat.id

        state = await self._get_support_state(user_id)
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
            user_id = query.from_user.id
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.CONFIRMATION
            state['current_step'] = 6
            await self._save_support_state(user_id, state)
            await self.show_confirmation_step(query, context)

    async def show_confirmation_step(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra etapa de confirmação."""
        user_id = query.from_user.id
        state = await self._get_support_state(user_id)
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
        user_id = query.from_user.id

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
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.CATEGORY
            state['current_step'] = 1
            await self._save_support_state(user_id, state)
            await self.show_category_step(query, context)
        elif callback_data == "sup_edit_game":
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.GAME
            state['current_step'] = 2
            await self._save_support_state(user_id, state)
            await self.show_game_step(query, context)
        elif callback_data == "sup_edit_timing":
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.TIMING
            state['current_step'] = 3
            await self._save_support_state(user_id, state)
            await self.show_timing_step(query, context)
        elif callback_data == "sup_edit_description":
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.DESCRIPTION
            state['current_step'] = 4
            await self._save_support_state(user_id, state)

            await query.edit_message_text(
                "📝 Digite a nova descrição do problema:",
                parse_mode='Markdown'
            )
        elif callback_data == "sup_edit_attachments":
            state = await self._get_support_state(user_id)
            state['state'] = SupportState.ATTACHMENTS
            state['current_step'] = 5
            await self._save_support_state(user_id, state)
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
        user = query.from_user
        user_id = user.id
        state = await self._get_support_state(user_id)

        try:
            await query.edit_message_text(
                "⏳ **Criando seu chamado...**\n\n"
                "Aguarde enquanto registro suas informações no sistema.",
                parse_mode='Markdown'
            )

            # 1. Montar a descrição enriquecida
            user_mention = f"@{user.username}" if user.username else f"ID: {user_id}"
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
                "user_id": user_id,
                "user_name": user.first_name,
                "user_telegram": user_mention,
                "user_phone": getattr(user, 'phone_number', None),  # Telefone do Telegram (se disponível)
                "category": state['category'],
                "game_name": state['game_name'],
                "timing": state['timing_name'],
                "description": enhanced_description,
                "attachments": state.get('attachments', [])
            }

            # 3. Chamar o Use Case correto
            logger.info(f"Iniciando criação de ticket para usuário {user_id} via Use Case...")
            hubsoft_use_case = self._ensure_hubsoft_use_case()
            hubsoft_result = await hubsoft_use_case.create_support_ticket(ticket_data)

            if not hubsoft_result.success:
                # Escapa caracteres especiais do Markdown no error_code
                error_code = hubsoft_result.error_code or 'CREATE_TICKET_ERROR'
                safe_error_code = error_code.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')

                error_message = (
                    "❌ *Não foi possível criar seu chamado*\n\n"
                    "Nosso sistema de suporte está temporariamente indisponível.\n\n"
                    f"*Código do erro:* `{safe_error_code}`\n\n"
                    "Por favor, tente novamente em alguns minutos."
                )
                await query.edit_message_text(error_message, parse_mode='Markdown')
                logger.error(f"Falha ao criar ticket para usuário {user_id}: {hubsoft_result.message}")
                return

            # 4. Montar mensagem de sucesso com o protocolo real
            hubsoft_protocol = hubsoft_result.data.get("protocolo") or f"ID {hubsoft_result.data.get('id_atendimento')}"
            attachments_uploaded = hubsoft_result.data.get('attachments_uploaded', 0)
            attachments_failed = hubsoft_result.data.get('attachments_failed', 0)
            now = datetime.now()

            # Monta informação sobre anexos
            attachments_info = ""
            if attachments_uploaded > 0:
                attachments_info = f"📎 **Anexos:** {attachments_uploaded} enviado(s) com sucesso!\n"
            if attachments_failed > 0:
                attachments_info += f"⚠️ {attachments_failed} anexo(s) com falha no envio\n"

            success_message = (
                f"🎉 **PRONTO! SEU CHAMADO FOI CRIADO COM SUCESSO!**\n\n"
                f"📋 **Protocolo:** `{hubsoft_protocol}`\n"
                f"📅 **Criado em:** {now.strftime('%d/%m/%Y às %H:%M')}\n"
                f"📊 **Status:** Aguardando Atendimento\n"
                f"{attachments_info}"
                f"\n"
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

            await self._clear_support_state(user_id)
            logger.info(f"Ticket {hubsoft_protocol} criado com sucesso para usuário {user_id}")

        except Exception as e:
            logger.error(f"Erro crítico ao criar ticket: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ *Erro ao criar chamado*\n\n"
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
        user_id = update.effective_user.id

        # Verifica se está em fluxo de suporte
        repository = self._ensure_support_session_repository()
        has_session = await repository.session_exists(user_id)

        if not has_session:
            # Verifica se teve uma sessão expirada recentemente
            had_expired = await repository.had_recent_expired_session(user_id, within_minutes=5)
            if had_expired:
                await update.message.reply_text(
                    "⏱️ **Sessão Expirada**\n\n"
                    "Sua sessão de suporte expirou por inatividade (24h).\n\n"
                    "Por favor, inicie um novo chamado com /suporte",
                    parse_mode='Markdown'
                )
                logger.info(f"Usuário {user_id} tentou continuar sessão expirada - notificado")
                return True
            return False

        state = await self._get_support_state(user_id)

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

            await self._save_support_state(user_id, state)

            # Mostra etapa de anexos
            await self.show_attachments_step(update.message, context)
            logger.info(f"Usuário {user_id} enviou descrição ({len(text)} chars)")
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
        user_id = user.id

        # Verifica se está em fluxo de suporte
        repository = self._ensure_support_session_repository()
        has_session = await repository.session_exists(user_id)

        if not has_session:
            # Verifica se teve uma sessão expirada recentemente
            had_expired = await repository.had_recent_expired_session(user_id, within_minutes=5)
            if had_expired:
                await update.message.reply_text(
                    "⏱️ **Sessão Expirada**\n\n"
                    "Sua sessão de suporte expirou por inatividade (24h).\n\n"
                    "Por favor, inicie um novo chamado com /suporte",
                    parse_mode='Markdown'
                )
                logger.info(f"Usuário {user_id} tentou enviar anexo em sessão expirada - notificado")
                return True
            return False

        state = await self._get_support_state(user_id)

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

        await self._save_support_state(user_id, state)

        attachments_count = len(attachments)

        # Mensagem de confirmação
        remaining = 3 - attachments_count
        await update.message.reply_text(
            f"✅ **Anexo {attachments_count}/3 recebido com sucesso!**\n\n"
            f"📸 Perfeito! Você ainda pode enviar mais **{remaining} foto(s)** se quiser, "
            f"ou clicar em **Continuar** para finalizar! 😊",
            parse_mode='Markdown'
        )

        logger.info(f"Usuário {user_id} enviou anexo {attachments_count}/3")
        return True
