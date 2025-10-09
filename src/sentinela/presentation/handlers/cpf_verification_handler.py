"""
CPF Verification Handler.

Handler especializado para fluxos de verificação de CPF,
incluindo input de CPF, lembretes e resolução de duplicatas.
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
from ...core.config import (
    TELEGRAM_GROUP_ID,
    ONCABO_SITE_URL,
    ONCABO_WHATSAPP_URL,
    INVITE_LINK_EXPIRE_TIME
)

logger = logging.getLogger(__name__)


class CPFVerificationHandler:
    """Handler para gerenciar todas as operações relacionadas a verificação de CPF."""

    def __init__(self, container):
        """
        Inicializa o handler de verificação de CPF.

        Args:
            container: DI Container com dependências.
        """
        self._container = container
        self._cpf_use_case: Optional[CPFVerificationUseCase] = None

    def _ensure_cpf_use_case(self) -> CPFVerificationUseCase:
        """Garante que o CPF use case está inicializado."""
        if self._cpf_use_case is None:
            self._cpf_use_case = self._container.get("cpf_verification_use_case")
        return self._cpf_use_case

    async def check_user_verified(self, user_id: int) -> bool:
        """
        Verifica se um usuário está ATIVO no sistema.

        A única fonte da verdade para um usuário ativo é a tabela `users`
        com o status 'active'.

        Args:
            user_id: ID do usuário do Telegram.

        Returns:
            bool: True se o usuário existe e está ativo, False caso contrário.
        """
        try:
            user_repo = self._container.get("user_repository")
            if not user_repo:
                logger.warning("UserRepository não disponível no container.")
                return False

            user = await user_repo.find_by_telegram_id(user_id)

            if user and user.is_active():
                logger.debug(f"Usuário {user_id} está verificado e ativo.")
                return True

            if user:
                logger.debug(f"Usuário {user_id} encontrado, mas com status '{user.status.value}', não 'active'.")
            else:
                logger.debug(f"Usuário {user_id} não encontrado na tabela 'users'.")

            return False

        except Exception as e:
            logger.error(f"Erro ao verificar status do usuário {user_id}: {e}", exc_info=True)
            return False

    async def get_verification_status_message(self, user_id: int) -> dict:
        """
        Retorna mensagem contextualizada baseada no status da verificação.

        Returns:
            dict: {
                "is_verified": bool,
                "status": str,
                "message": str
            }
        """
        try:
            cpf_repo = self._container.get("cpf_verification_repository")
            if not cpf_repo:
                return {
                    "is_verified": False,
                    "status": "unknown",
                    "message": "⚠️ Sistema de verificação indisponível.\n\nTente novamente mais tarde."
                }

            verifications = await cpf_repo.find_by_user_id(user_id, limit=10)

            if not verifications:
                return {
                    "is_verified": False,
                    "status": "no_verification",
                    "message": "⚠️ Nenhuma verificação encontrada.\n\nDigite /start para iniciar."
                }

            latest = verifications[0]

            from ...domain.entities.cpf_verification import VerificationStatus

            completed = next((v for v in verifications if v.status == VerificationStatus.COMPLETED), None)
            if completed:
                return {
                    "is_verified": True,
                    "status": "completed",
                    "message": ""
                }

            status_messages = {
                VerificationStatus.PENDING: {
                    "message": "⏳ **Aguardando verificação de CPF**\n\n📝 Por favor, envie seu CPF (apenas números) para continuar.\n\nDigite /ajuda se precisar de mais informações."
                },
                VerificationStatus.IN_PROGRESS: {
                    "message": "🔄 **Verificação em andamento**\n\nAguarde enquanto processamos suas informações.\n\nEm caso de dúvidas, digite /ajuda"
                },
                VerificationStatus.FAILED: {
                    "message": "❌ **Verificação não concluída**\n\nSuas tentativas foram esgotadas ou houve um erro.\n\n🔄 Para tentar novamente, digite /start"
                },
                VerificationStatus.CANCELLED: {
                    "message": "🚫 **Verificação cancelada**\n\nVocê cancelou o processo de verificação.\n\n🔄 Para tentar novamente, digite /start"
                },
                VerificationStatus.EXPIRED: {
                    "message": "⏱️ **Verificação expirada**\n\nO prazo para verificação expirou.\n\n🔄 Para tentar novamente, digite /start"
                }
            }

            status_info = status_messages.get(
                latest.status,
                {"message": "⚠️ Status desconhecido. Digite /start para reiniciar."}
            )

            return {
                "is_verified": False,
                "status": latest.status.value,
                "message": status_info["message"]
            }

        except Exception as e:
            logger.error(f"Erro ao obter mensagem de status: {e}")
            return {
                "is_verified": False,
                "status": "error",
                "message": "⚠️ Erro ao verificar status. Digite /start"
            }

    async def handle_cpf_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        cpf: str
    ) -> None:
        """Processa entrada de CPF e cria link de acesso ao grupo se válido."""
        user = update.effective_user

        try:
            processing_msg = await update.message.reply_text(
                "🔍 <b>Verificando seu CPF...</b>\n\n"
                "Aguarde um momento enquanto consulto nossa base de dados.",
                parse_mode='HTML'
            )

            cpf_use_case = self._ensure_cpf_use_case()
            result = await cpf_use_case.submit_cpf(
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
                        await update.message.reply_text(
                            "❌ Encontrei um conflito com este CPF, mas não consegui obter os detalhes. "
                            "Por favor, contate o suporte."
                        )

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
                        message = (
                            "✅ **CPF Verificado!** 🎉\n\n"
                            "Seu plano está ativo, mas houve um erro ao gerar seu link de convite. "
                            "Por favor, contate o suporte."
                        )

                    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)

            # CASO 3: Falha na Verificação (Contrato inativo, etc.)
            else:
                message = (
                    "❌ <b>Ops! Não encontrei seu CPF vinculado a um plano OnCabo Gaming ativo.</b>\n\n"
                    "Infelizmente, o acesso ao grupo é exclusivo para assinantes do plano OnCabo Gaming.\n\n"
                    "📌 <b>QUER FAZER PARTE?</b>\n"
                    f"Acesse nosso site em {ONCABO_SITE_URL} ou fale conosco pelo WhatsApp em {ONCABO_WHATSAPP_URL} "
                    "para contratar e entrar na comunidade!\n\n"
                    "Estamos te esperando! 🚀"
                )
                await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=False)

            # Limpa estado de aguardando CPF e remove o job de lembrete
            if 'waiting_cpf' in context.user_data:
                del context.user_data['waiting_cpf']

            job_name = f"cpf_reminder_{user.id}"
            jobs = context.job_queue.get_jobs_by_name(job_name)
            if jobs:
                for job in jobs:
                    job.schedule_removal()
                logger.info(f"Job de lembrete de CPF '{job_name}' removido com sucesso.")

        except Exception as e:
            logger.error(f"Erro ao processar CPF: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ <b>Erro ao verificar CPF.</b>\n\n"
                "Tente novamente ou entre em contato com o suporte.",
                parse_mode='HTML'
            )

    async def handle_duplicate_resolution_callback(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
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
                await query.edit_message_text(
                    "❌ Ops! Perdi o contexto desta conversa. Por favor, tente verificar seu CPF novamente."
                )
                return

            duplicate_users = resolution_context.get('conflicting_users', [])
            duplicate_user_ids = [u.get('user_id') for u in duplicate_users]

            # Chama o Use Case para resolver o conflito
            cpf_use_case = self._ensure_cpf_use_case()
            result = await cpf_use_case.resolve_duplicate_conflict(
                verification_id=verification_id,
                primary_user_id=query.from_user.id,
                duplicate_user_ids=duplicate_user_ids
            )

            if result.success and result.data.get('verified'):
                # A resolução foi um sucesso e a verificação foi completada.
                try:
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
                    await query.edit_message_text(
                        "✅ Conflito resolvido, mas houve um erro ao gerar seu link de convite. "
                        "Por favor, contate o suporte."
                    )
            else:
                # A resolução falhou
                await query.edit_message_text(
                    f"❌ Ops! Ocorreu um erro ao tentar resolver o conflito: {result.message}. "
                    "Por favor, contate o suporte."
                )

            # Limpa o contexto da resolução
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']

        elif action == "cancel":
            logger.info(f"Usuário {query.from_user.id} cancelou a resolução de conflito para a verificação {verification_id}.")

            # Chama o use case para cancelar a verificação
            cpf_use_case = self._ensure_cpf_use_case()
            result = await cpf_use_case.cancel_verification_by_id(
                verification_id=verification_id,
                reason="conflict_cancelled_by_user"
            )

            if result.success:
                await query.edit_message_text(
                    "🚫 **Verificação Cancelada**\n\n"
                    "Você cancelou a resolução do conflito de CPF.\n\n"
                    "Para tentar novamente com outro CPF, por favor, use o comando /start.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Erro ao cancelar: {result.message}\n\n"
                    "Por favor, entre em contato com o suporte.",
                    parse_mode='Markdown'
                )

            # Limpa o contexto da resolução
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']

    async def cpf_reminder_callback(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Envia um lembrete para o usuário que não enviou o CPF a tempo."""
        job = context.job
        user_id = job.data['user_id']

        logger.info(f"Executando lembrete de CPF para usuário {user_id}.")

        # Acessa o user_data específico do usuário
        user_context = context.application.user_data.get(user_id, {})

        # Verifica se o usuário ainda está aguardando o CPF
        if user_context.get('waiting_cpf'):
            logger.info(f"Usuário {user_id} ainda não enviou o CPF. Enviando lembrete.")
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=(
                    "👋 Olá! Só um lembrete amigável de que estou aguardando seu CPF para continuarmos com a verificação. "
                    "Pode me enviar apenas os números, por favor? 😊"
                )
            )
        else:
            logger.info(f"Lembrete de CPF para {user_id} ignorado, pois o usuário não está mais aguardando CPF.")

    def schedule_cpf_reminder(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        delay_seconds: int = 300
    ) -> None:
        """
        Agenda um lembrete de CPF para um usuário.

        Args:
            context: Contexto do bot
            user_id: ID do usuário
            delay_seconds: Delay em segundos (padrão: 300 = 5 minutos)
        """
        job_name = f"cpf_reminder_{user_id}"

        # Remove job antigo se existir, para evitar duplicatas
        jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in jobs:
            job.schedule_removal()
            logger.debug(f"Job de lembrete antigo {job_name} removido.")

        context.job_queue.run_once(
            self.cpf_reminder_callback,
            delay_seconds,
            chat_id=user_id,
            name=job_name,
            data={'user_id': user_id}
        )
        logger.info(f"Lembrete de CPF agendado para usuário {user_id} em {delay_seconds} segundos. Job: {job_name}")
