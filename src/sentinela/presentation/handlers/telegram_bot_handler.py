"""
Telegram Bot Handler.

Camada de apresentação para integração com Telegram Bot,
utilizando a nova arquitetura com dependency injection.
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...infrastructure.config.container import get_container
from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
from ...application.use_cases.admin_operations_use_case import AdminOperationsUseCase
from ...domain.value_objects.identifiers import UserId

logger = logging.getLogger(__name__)


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
        """Processa comando /suporte."""
        try:
            await self._ensure_initialized()

            user = update.effective_user
            chat_id = update.effective_chat.id
            is_group = chat_id != user.id

            if not user:
                return

            # Se foi enviado no grupo, deleta o comando e avisa que respondeu no privado
            if is_group:
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ @{user.username or user.first_name}, respondi seu comando /suporte no **privado**!",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Não foi possível deletar comando do grupo: {e}")

            # Cria teclado de categorias
            keyboard = [
                [
                    InlineKeyboardButton("🌐 Conectividade/Ping", callback_data="cat_connectivity"),
                    InlineKeyboardButton("⚡ Performance/FPS", callback_data="cat_performance")
                ],
                [
                    InlineKeyboardButton("🎮 Problemas no Jogo", callback_data="cat_game_issues"),
                    InlineKeyboardButton("💻 Configuração", callback_data="cat_configuration")
                ],
                [
                    InlineKeyboardButton("📞 Outros", callback_data="cat_others")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                "🎯 **Criar Ticket de Suporte**\n\n"
                "Selecione a categoria que melhor descreve seu problema:"
            )

            # SEMPRE responde no privado do usuário
            await context.bot.send_message(
                chat_id=user.id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            logger.info(f"Usuário {user.id} iniciou criação de ticket")

        except Exception as e:
            logger.error(f"Erro no comando /suporte: {e}")
            # Erro também vai para privado
            await context.bot.send_message(
                chat_id=user.id,
                text="❌ Erro ao iniciar suporte. Tente novamente."
            )

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

            if callback_data.startswith("cat_"):
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