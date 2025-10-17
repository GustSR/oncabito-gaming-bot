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

                        # Salva o contexto para o callback (em memória E no banco)
                        context.user_data['duplicate_resolution_context'] = {
                            'verification_id': verification_id,
                            'conflicting_users': conflicting_users
                        }

                        # CORREÇÃO INCONSISTÊNCIA #2: Persiste contexto no banco
                        # para sobreviver reinicializações do bot
                        try:
                            from ...domain.entities.cpf_verification import VerificationId as VerId
                            verification_repo = self._container.get("cpf_verification_repository")
                            verification = await verification_repo.find_by_id(VerId(verification_id))
                            if verification:
                                verification.set_duplicate_resolution_context(
                                    conflicting_users=conflicting_users,
                                    verification_id=verification_id
                                )
                                await verification_repo.save(verification)
                                logger.info(f"Contexto de resolução de duplicatas persistido no banco para verificação {verification_id}")
                        except Exception as ctx_error:
                            logger.error(f"Erro ao persistir contexto de resolução: {ctx_error}")

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

            # CORREÇÃO BUG #13: Limpa TODOS os contextos relacionados à verificação
            if 'waiting_cpf' in context.user_data:
                del context.user_data['waiting_cpf']

            # Limpa contexto de resolução de duplicatas (se existir)
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']
                logger.debug(f"Contexto de resolução de duplicatas limpo para usuário {user.id}")

            # Remove job de lembrete de CPF
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
        """
        Processa a escolha do usuário na resolução de CPF duplicado.

        Suporta dois fluxos:
        1. Fluxo reativo (verificação): dup_resolve_merge_{verification_id} ou dup_resolve_cancel_{verification_id}
        2. Fluxo proativo (checkup): resolve_dup:{conflict_id}:{chosen_user_id} ou resolve:{short_id}:{chosen_user_id}
        """
        await query.edit_message_text("⏳ Processando sua escolha...", parse_mode='Markdown')

        # Detecta qual fluxo está sendo usado
        if callback_data.startswith("resolve_dup:") or callback_data.startswith("resolve:"):
            # NOVO FLUXO: Resolução proativa (via checkup diário)
            await self._handle_proactive_duplicate_resolution(query, callback_data)
        else:
            # FLUXO ANTIGO: Resolução reativa (via verificação de CPF)
            await self._handle_reactive_duplicate_resolution(query, context, callback_data)

    async def _handle_proactive_duplicate_resolution(
        self,
        query,
        callback_data: str
    ) -> None:
        """Processa resolução de duplicata proativa (detectada no checkup)."""
        try:
            # Parse callback: resolve_dup:{conflict_id}:{chosen_user_id} ou resolve:{short_id}:{chosen_user_id}
            parts = callback_data.split(':')
            if len(parts) != 3:
                await query.edit_message_text(
                    "❌ Formato de callback inválido. Por favor, contate o suporte.",
                    parse_mode='Markdown'
                )
                return

            conflict_id = parts[1]
            chosen_user_id = int(parts[2])

            logger.info(f"Resolução proativa: usuário {query.from_user.id} escolheu manter conta {chosen_user_id} (conflict: {conflict_id})")

            # Carrega o conflito do repositório
            from ...domain.entities.duplicate_conflict import ConflictId
            conflict_repo = self._container.get("duplicate_conflict_repository")
            conflict = await conflict_repo.find_by_id(ConflictId(conflict_id))

            if not conflict:
                await query.edit_message_text(
                    "❌ Conflito não encontrado. Talvez já tenha sido resolvido.\n\n"
                    "Se o problema persistir, contate o suporte.",
                    parse_mode='Markdown'
                )
                return

            # Verifica se o conflito ainda está pendente
            from ...domain.entities.duplicate_conflict import ConflictStatus
            if conflict.status != ConflictStatus.PENDING:
                await query.edit_message_text(
                    f"⚠️ Este conflito já foi resolvido anteriormente (status: {conflict.status.value}).\n\n"
                    "Nenhuma ação adicional é necessária.",
                    parse_mode='Markdown'
                )
                return

            # Valida que o escolhido está na lista de usuários do conflito
            if chosen_user_id not in conflict.user_ids:
                await query.edit_message_text(
                    "❌ Usuário escolhido não faz parte deste conflito. Por favor, contate o suporte.",
                    parse_mode='Markdown'
                )
                return

            # Resolve o conflito
            conflict.resolve_by_user_choice(
                chosen_user_id=chosen_user_id,
                resolved_by=query.from_user.id
            )

            # Identifica os usuários a serem removidos
            users_to_remove = [uid for uid in conflict.user_ids if uid != chosen_user_id]

            # Remove os outros usuários do grupo
            user_repo = self._container.get("user_repository")
            from ...domain.value_objects.identifiers import UserId
            from telegram.error import TelegramError

            removal_failed_users = []
            for user_id in users_to_remove:
                try:
                    # CORREÇÃO BUG #11: Verifica se bot tem permissões antes de tentar remover
                    try:
                        bot_member = await query.get_bot().get_chat_member(int(TELEGRAM_GROUP_ID), query.get_bot().id)
                        if not bot_member.can_restrict_members:
                            logger.error(f"Bot não tem permissão 'can_restrict_members' para remover usuário {user_id}")
                            removal_failed_users.append(user_id)
                            continue
                    except TelegramError as perm_error:
                        logger.error(f"Erro ao verificar permissões do bot: {perm_error}")
                        removal_failed_users.append(user_id)
                        continue

                    # Remove do grupo do Telegram
                    await query.get_bot().ban_chat_member(chat_id=int(TELEGRAM_GROUP_ID), user_id=user_id)
                    await query.get_bot().unban_chat_member(chat_id=int(TELEGRAM_GROUP_ID), user_id=user_id)

                    # Desativa o usuário no banco
                    user = await user_repo.find_by_id(UserId(user_id))
                    if user:
                        reason = f"CPF transferido para a conta {chosen_user_id} por escolha do usuário"
                        user.deactivate(reason)
                        await user_repo.save(user)
                        logger.info(f"Usuário {user_id} removido e desativado (resolução proativa)")

                    # Envia DM explicando a remoção
                    try:
                        await query.get_bot().send_message(
                            chat_id=user_id,
                            text=(
                                "⚠️ **Atualização de Conta**\n\n"
                                f"Seu CPF foi transferido para outra conta do Telegram (ID: {chosen_user_id}).\n\n"
                                "Como resultado, você foi removido do grupo OnCabo Gaming.\n\n"
                                "Se você acredita que isso foi um erro, por favor entre em contato com o suporte."
                            ),
                            parse_mode='Markdown'
                        )
                    except Exception as dm_error:
                        logger.warning(f"Não foi possível enviar DM para usuário {user_id}: {dm_error}")

                except TelegramError as removal_error:
                    # Erros do Telegram ao remover usuário (permissões, usuário já saiu, etc.)
                    logger.error(f"Erro do Telegram ao remover usuário {user_id}: {removal_error}")
                    removal_failed_users.append(user_id)
                except Exception as removal_error:
                    logger.error(f"Erro inesperado ao remover usuário {user_id}: {removal_error}")
                    removal_failed_users.append(user_id)

            # Se houve falhas de remoção, marca conflito como erro e notifica
            if removal_failed_users:
                logger.error(f"⚠️ Falha ao remover {len(removal_failed_users)} usuários: {removal_failed_users}")
                # Marca conflito como tendo erros
                conflict.resolution_notes = f"Falha ao remover usuários: {removal_failed_users}"

            # Salva o conflito resolvido
            await conflict_repo.save(conflict)

            # Cria link de convite para a conta escolhida (se não for ele mesmo)
            client_name = query.from_user.first_name
            invite_message = ""

            if chosen_user_id != query.from_user.id:
                # A conta escolhida é diferente da conta que está respondendo
                # (caso improvável, mas possível se admin responder)
                invite_message = (
                    f"\n\n⚠️ **Nota:** A conta mantida é o ID {chosen_user_id}, não a sua. "
                    f"Um link de convite foi enviado para o usuário correspondente."
                )
            else:
                # A conta escolhida é a mesma que respondeu - gera link de convite
                try:
                    invite_link = await query.get_bot().create_chat_invite_link(
                        chat_id=int(TELEGRAM_GROUP_ID),
                        member_limit=1,
                        name=f"Link para {client_name} (pós-resolução)"
                    )
                    invite_message = (
                        f"\n\n🔗 **Seu link de acesso ao grupo:**\n"
                        f"{invite_link.invite_link}\n\n"
                        f"⏰ Este link é pessoal e pode ser usado apenas 1 vez!"
                    )
                except Exception as link_error:
                    logger.error(f"Erro ao criar link de convite: {link_error}")
                    invite_message = (
                        "\n\n⚠️ Houve um erro ao gerar seu link de convite. "
                        "Por favor, contate o suporte."
                    )

            # Mensagem de sucesso
            success_message = (
                f"✅ **Conflito Resolvido com Sucesso!**\n\n"
                f"A conta escolhida (ID: {chosen_user_id}) foi mantida com o CPF.\n"
                f"As outras {len(users_to_remove)} conta(s) foram removidas do grupo."
                f"{invite_message}"
            )

            await query.edit_message_text(success_message, parse_mode='Markdown', disable_web_page_preview=True)
            logger.info(f"Conflito {conflict_id} resolvido com sucesso por usuário {query.from_user.id}")

        except Exception as e:
            logger.error(f"Erro ao processar resolução proativa de duplicata: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Ocorreu um erro ao processar sua escolha.\n\n"
                "Por favor, contate o suporte.",
                parse_mode='Markdown'
            )

    async def _handle_reactive_duplicate_resolution(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        callback_data: str
    ) -> None:
        """Processa resolução de duplicata reativa (durante verificação de CPF)."""
        parts = callback_data.split('_')
        action = parts[2]
        verification_id = parts[3]

        if action == "merge":
            logger.info(f"Usuário {query.from_user.id} escolheu 'merge' para a verificação {verification_id}.")

            # CORREÇÃO INCONSISTÊNCIA #2: Tenta recuperar contexto da memória,
            # mas se não encontrar, recupera do banco (para sobreviver restarts)
            resolution_context = context.user_data.get('duplicate_resolution_context')

            if not resolution_context or resolution_context.get('verification_id') != verification_id:
                logger.warning(f"Contexto não encontrado em memória para verificação {verification_id}. Tentando recuperar do banco...")

                try:
                    from ...domain.entities.cpf_verification import VerificationId as VerId
                    verification_repo = self._container.get("cpf_verification_repository")
                    verification = await verification_repo.find_by_id(VerId(verification_id))

                    if verification and verification.has_pending_duplicate_resolution():
                        resolution_context = verification.duplicate_resolution_context
                        logger.info(f"Contexto recuperado do banco para verificação {verification_id}")
                    else:
                        await query.edit_message_text(
                            "❌ Ops! Perdi o contexto desta conversa e não consegui recuperá-lo. "
                            "Por favor, tente verificar seu CPF novamente."
                        )
                        return
                except Exception as e:
                    logger.error(f"Erro ao recuperar contexto do banco: {e}")
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

            # CORREÇÃO INCONSISTÊNCIA #2: Limpa o contexto da resolução (memória + banco)
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']

            # Limpa do banco também
            try:
                from ...domain.entities.cpf_verification import VerificationId as VerId
                verification_repo = self._container.get("cpf_verification_repository")
                verification = await verification_repo.find_by_id(VerId(verification_id))
                if verification and verification.has_pending_duplicate_resolution():
                    verification.clear_duplicate_resolution_context()
                    await verification_repo.save(verification)
                    logger.info(f"Contexto de resolução limpo do banco para verificação {verification_id}")
            except Exception as ctx_error:
                logger.error(f"Erro ao limpar contexto do banco: {ctx_error}")

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

            # CORREÇÃO INCONSISTÊNCIA #2: Limpa o contexto da resolução (memória + banco)
            if 'duplicate_resolution_context' in context.user_data:
                del context.user_data['duplicate_resolution_context']
            if 'waiting_cpf' in context.user_data:
                del context.user_data['waiting_cpf']

            # Limpa do banco também
            try:
                from ...domain.entities.cpf_verification import VerificationId as VerId
                verification_repo = self._container.get("cpf_verification_repository")
                verification = await verification_repo.find_by_id(VerId(verification_id))
                if verification and verification.has_pending_duplicate_resolution():
                    verification.clear_duplicate_resolution_context()
                    await verification_repo.save(verification)
                    logger.info(f"Contexto de resolução limpo do banco para verificação {verification_id}")
            except Exception as ctx_error:
                logger.error(f"Erro ao limpar contexto do banco: {ctx_error}")

    async def cpf_reminder_callback(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Envia um lembrete para o usuário que não enviou o CPF a tempo."""
        job = context.job
        user_id = job.data['user_id']

        logger.info(f"Executando lembrete de CPF para usuário {user_id}.")

        try:
            # CORREÇÃO BUG #2: Verifica status direto no banco de dados (fonte da verdade)
            # ao invés de usar context.user_data que pode estar desatualizado
            cpf_repo = self._container.get("cpf_verification_repository")
            if not cpf_repo:
                logger.warning(f"CPF repository não disponível. Cancelando lembrete para {user_id}.")
                return

            # Busca verificações pendentes
            from ...domain.entities.cpf_verification import VerificationStatus
            verifications = await cpf_repo.find_by_user_id(user_id, limit=5)

            # Verifica se existe alguma verificação PENDENTE (não processada ainda)
            has_pending = any(v.status == VerificationStatus.PENDING for v in verifications)

            if has_pending:
                logger.info(f"Usuário {user_id} ainda tem verificação pendente. Enviando lembrete.")
                await context.bot.send_message(
                    chat_id=job.chat_id,
                    text=(
                        "👋 Olá! Só um lembrete amigável de que estou aguardando seu CPF para continuarmos com a verificação. "
                        "Pode me enviar apenas os números, por favor? 😊"
                    )
                )
            else:
                logger.info(f"Lembrete de CPF para {user_id} ignorado. Verificação já foi processada ou não existe mais.")

        except Exception as e:
            logger.error(f"Erro ao processar lembrete de CPF para {user_id}: {e}", exc_info=True)

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
