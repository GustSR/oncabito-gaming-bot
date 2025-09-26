import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from src.sentinela.core.config import TELEGRAM_TOKEN
from src.sentinela.clients.db_client import get_db_connection, save_user_data, get_user_by_cpf
from src.sentinela.integrations.hubsoft.cliente import get_client_data
from src.sentinela.services.group_service import remove_user_from_group

logger = logging.getLogger(__name__)

class CPFVerificationService:
    """Serviço para gerenciar re-verificações de CPF"""

    @staticmethod
    def create_pending_verification(user_id: int, username: str, user_mention: str,
                                  verification_type: str = "auto_checkup",
                                  source_action: str = None) -> bool:
        """
        Cria uma verificação pendente de CPF

        Args:
            user_id: ID do usuário no Telegram
            username: Nome de usuário
            user_mention: Mention formatado
            verification_type: Tipo de verificação (auto_checkup, support_request)
            source_action: Ação que originou a verificação
        """
        try:
            expires_at = datetime.now() + timedelta(hours=24)

            with get_db_connection() as conn:
                # Remove verificação anterior se existir
                conn.execute("""
                    DELETE FROM pending_cpf_verifications
                    WHERE user_id = ?
                """, (user_id,))

                # Cria nova verificação
                conn.execute("""
                    INSERT INTO pending_cpf_verifications (
                        user_id, username, user_mention, expires_at,
                        verification_type, source_action
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, user_mention, expires_at, verification_type, source_action))

                conn.commit()

                logger.info(f"Verificação pendente criada para usuário {username} (ID: {user_id})")
                return True

        except Exception as e:
            logger.error(f"Erro ao criar verificação pendente para {user_id}: {e}")
            return False

    @staticmethod
    def get_pending_verification(user_id: int) -> dict:
        """Busca verificação pendente para um usuário"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM pending_cpf_verifications
                    WHERE user_id = ? AND status = 'pending'
                """, (user_id,))

                result = cursor.fetchone()
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Erro ao buscar verificação pendente para {user_id}: {e}")
            return None

    @staticmethod
    def update_verification_attempt(user_id: int) -> bool:
        """Atualiza contador de tentativas de verificação"""
        try:
            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE pending_cpf_verifications
                    SET attempts = attempts + 1, last_attempt_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Erro ao atualizar tentativas para {user_id}: {e}")
            return False

    @staticmethod
    def complete_verification(user_id: int, success: bool, cpf_provided: str = None,
                            failure_reason: str = None) -> bool:
        """
        Completa uma verificação de CPF

        Args:
            user_id: ID do usuário
            success: Se a verificação foi bem-sucedida
            cpf_provided: CPF fornecido pelo usuário
            failure_reason: Razão da falha (se aplicável)
        """
        try:
            with get_db_connection() as conn:
                # Busca dados da verificação pendente
                cursor = conn.execute("""
                    SELECT * FROM pending_cpf_verifications
                    WHERE user_id = ? AND status = 'pending'
                """, (user_id,))

                verification = cursor.fetchone()
                if not verification:
                    logger.warning(f"Nenhuma verificação pendente encontrada para {user_id}")
                    return False

                verification_dict = dict(verification)

                # Atualiza status da verificação pendente
                new_status = 'completed' if success else 'failed'
                conn.execute("""
                    UPDATE pending_cpf_verifications
                    SET status = ?, last_attempt_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_status, user_id))

                # Adiciona ao histórico
                conn.execute("""
                    INSERT INTO cpf_verification_history (
                        user_id, username, verification_type, source_action,
                        status, cpf_provided, success, completed_at, failure_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (
                    user_id,
                    verification_dict['username'],
                    verification_dict['verification_type'],
                    verification_dict['source_action'],
                    new_status,
                    cpf_provided,
                    success,
                    failure_reason
                ))

                conn.commit()

                logger.info(f"Verificação completada para {user_id}: {'sucesso' if success else 'falha'}")
                return True

        except Exception as e:
            logger.error(f"Erro ao completar verificação para {user_id}: {e}")
            return False

    @staticmethod
    def get_expired_verifications() -> list:
        """Retorna verificações expiradas"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM pending_cpf_verifications
                    WHERE status = 'pending' AND expires_at < CURRENT_TIMESTAMP
                """)

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Erro ao buscar verificações expiradas: {e}")
            return []

    @staticmethod
    async def send_cpf_verification_request(user_id: int, username: str, verification_type: str):
        """
        Envia mensagem solicitando verificação de CPF

        Args:
            user_id: ID do usuário
            username: Nome de usuário
            verification_type: Tipo de verificação
        """
        try:
            if verification_type == "support_request":
                title = "🎮 Verificação necessária para suporte"
                context = "Para abrir um chamado de suporte"
                urgency = "Isso é necessário para continuar com seu atendimento."
            else:  # auto_checkup
                title = "🔍 Verificação de segurança necessária"
                context = "Para manter seu acesso ao grupo"
                urgency = "Você tem 24 horas para confirmar, caso contrário será removido do grupo."

            message = (
                f"{title}\n\n"
                f"Olá! Preciso confirmar seus dados {context}.\n\n"
                f"🔐 <b>Por segurança, preciso que você confirme seu CPF novamente.</b>\n\n"
                f"📝 <b>Como proceder:</b>\n"
                f"• Digite apenas os 11 números do seu CPF\n"
                f"• Exemplo: 12345678901\n"
                f"• Seus dados serão verificados em nosso sistema\n\n"
                f"⏰ <b>Prazo:</b> {urgency}\n\n"
                f"🛡️ <b>Seus dados estão seguros</b> - usamos o mesmo sistema do registro inicial.\n\n"
                f"📲 <b>Digite seu CPF agora:</b>"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="cpf_verification_cancel")]
            ])

            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )

            logger.info(f"Solicitação de verificação enviada para {username} (ID: {user_id})")

        except TelegramError as e:
            logger.error(f"Erro do Telegram ao enviar verificação para {user_id}: {e}")
        except Exception as e:
            logger.error(f"Erro ao enviar verificação para {user_id}: {e}")

    @staticmethod
    async def process_cpf_verification(user_id: int, username: str, cpf: str) -> dict:
        """
        Processa verificação de CPF fornecido

        Args:
            user_id: ID do usuário
            username: Nome de usuário
            cpf: CPF fornecido

        Returns:
            dict: Resultado da verificação
        """
        try:
            # Busca verificação pendente
            verification = CPFVerificationService.get_pending_verification(user_id)
            if not verification:
                return {
                    'success': False,
                    'reason': 'no_pending_verification',
                    'message': 'Não há verificação pendente para você.'
                }

            # Atualiza tentativas
            CPFVerificationService.update_verification_attempt(user_id)

            # Limpa e valida CPF
            clean_cpf = "".join(filter(str.isdigit, cpf))

            if len(clean_cpf) != 11:
                return {
                    'success': False,
                    'reason': 'invalid_cpf_format',
                    'message': 'CPF deve ter exatamente 11 dígitos.'
                }

            # Verifica no HubSoft
            logger.info(f"Verificando CPF {clean_cpf} no HubSoft para {username}")
            client_data = get_client_data(clean_cpf)

            if not client_data:
                CPFVerificationService.complete_verification(
                    user_id, False, clean_cpf, "cpf_not_found_hubsoft"
                )
                return {
                    'success': False,
                    'reason': 'cpf_not_found',
                    'message': 'CPF não encontrado em nossa base de clientes ativos.'
                }

            # VERIFICA DUPLICIDADE DE CPF
            existing_user = get_user_by_cpf(clean_cpf)
            if existing_user and existing_user['user_id'] != user_id:
                logger.warning(f"CPF duplicado detectado. CPF {clean_cpf} já está em uso pelo user_id {existing_user['user_id']}")
                return {
                    'success': False,
                    'reason': 'duplicate_cpf',
                    'message': 'Este CPF já está sendo usado por outra conta no Telegram.',
                    'existing_user_id': existing_user['user_id'],
                    'existing_username': existing_user.get('username', 'N/A')
                }

            # Salva dados do cliente no banco local
            if save_user_data(user_id, username, clean_cpf, client_data):
                CPFVerificationService.complete_verification(
                    user_id, True, clean_cpf
                )

                logger.info(f"Verificação bem-sucedida para {username} - dados salvos")

                return {
                    'success': True,
                    'client_data': client_data,
                    'message': 'CPF verificado com sucesso! Seus dados foram atualizados.'
                }
            else:
                CPFVerificationService.complete_verification(
                    user_id, False, clean_cpf, "database_save_error"
                )
                return {
                    'success': False,
                    'reason': 'database_error',
                    'message': 'Erro interno ao salvar dados. Tente novamente.'
                }

        except Exception as e:
            logger.error(f"Erro ao processar verificação de CPF para {user_id}: {e}")
            CPFVerificationService.complete_verification(
                user_id, False, cpf, f"system_error: {str(e)}"
            )
            return {
                'success': False,
                'reason': 'system_error',
                'message': 'Erro interno do sistema. Tente novamente mais tarde.'
            }

    @staticmethod
    async def send_verification_result(user_id: int, result: dict, verification_type: str):
        """Envia resultado da verificação para o usuário"""
        try:
            if result['success']:
                client_data = result['client_data']

                if verification_type == "support_request":
                    message = (
                        f"✅ <b>Verificação concluída com sucesso!</b>\n\n"
                        f"👤 <b>Cliente:</b> {client_data.get('nome', 'N/A')}\n"
                        f"📦 <b>Serviço:</b> {client_data.get('servico_nome', 'N/A')}\n"
                        f"✅ <b>Status:</b> {client_data.get('servico_status', 'N/A')}\n\n"
                        f"🎮 <b>Agora você pode usar o /suporte normalmente!</b>\n\n"
                        f"Use o comando /suporte para abrir seu chamado."
                    )
                else:  # auto_checkup
                    message = (
                        f"✅ <b>Verificação concluída com sucesso!</b>\n\n"
                        f"👤 <b>Cliente:</b> {client_data.get('nome', 'N/A')}\n"
                        f"📦 <b>Serviço:</b> {client_data.get('servico_nome', 'N/A')}\n"
                        f"✅ <b>Status:</b> {client_data.get('servico_status', 'N/A')}\n\n"
                        f"🛡️ <b>Seu acesso ao grupo foi confirmado!</b>\n\n"
                        f"Obrigado por manter seus dados atualizados."
                    )
            else:
                attempts_left = 3 - CPFVerificationService.get_pending_verification(user_id).get('attempts', 0)

                message = (
                    f"❌ <b>Verificação falhou</b>\n\n"
                    f"💬 <b>Motivo:</b> {result['message']}\n\n"
                )

                if attempts_left > 0:
                    message += (
                        f"🔄 <b>Você ainda tem {attempts_left} tentativa(s)</b>\n\n"
                        f"📝 Digite seu CPF novamente (apenas números):"
                    )
                else:
                    message += (
                        f"⏰ <b>Muitas tentativas falharam</b>\n\n"
                        f"Entre em contato com nosso suporte se precisar de ajuda."
                    )

            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Erro ao enviar resultado de verificação para {user_id}: {e}")

    @staticmethod
    async def cleanup_expired_verifications():
        """Remove usuários com verificações expiradas do grupo"""
        try:
            expired_verifications = CPFVerificationService.get_expired_verifications()

            if not expired_verifications:
                logger.info("Nenhuma verificação expirada encontrada")
                return

            logger.info(f"Processando {len(expired_verifications)} verificação(ões) expirada(s)")

            for verification in expired_verifications:
                user_id = verification['user_id']
                username = verification['username']
                verification_type = verification['verification_type']

                try:
                    # Marca como expirada
                    CPFVerificationService.complete_verification(
                        user_id, False, None, "verification_expired"
                    )

                    # Remove do grupo se foi verificação de checkup
                    if verification_type == "auto_checkup":
                        removal_success = await remove_user_from_group(
                            user_id, "Verificação de CPF expirada"
                        )

                        if removal_success:
                            logger.info(f"Usuário {username} (ID: {user_id}) removido por verificação expirada")
                        else:
                            logger.warning(f"Falha ao remover usuário {user_id} do grupo")

                    # Envia notificação de expiração
                    await CPFVerificationService.send_expiration_notice(user_id, verification_type)

                except Exception as e:
                    logger.error(f"Erro ao processar verificação expirada para {user_id}: {e}")

        except Exception as e:
            logger.error(f"Erro na limpeza de verificações expiradas: {e}")

    @staticmethod
    async def send_expiration_notice(user_id: int, verification_type: str):
        """Envia aviso de verificação expirada"""
        try:
            if verification_type == "support_request":
                message = (
                    f"⏰ <b>Verificação expirada</b>\n\n"
                    f"O prazo para confirmar seu CPF expirou.\n\n"
                    f"🔄 Para usar o suporte, digite /suporte novamente e confirme seus dados."
                )
            else:  # auto_checkup
                message = (
                    f"⏰ <b>Verificação expirada - Removido do grupo</b>\n\n"
                    f"Você foi removido do grupo por não confirmar seu CPF no prazo.\n\n"
                    f"🔄 <b>Para voltar:</b>\n"
                    f"1. Solicite um novo convite\n"
                    f"2. Use /start para registrar seu CPF\n"
                    f"3. Confirme seus dados corretamente\n\n"
                    f"📞 Se precisar de ajuda, entre em contato com nosso suporte."
                )

            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Erro ao enviar aviso de expiração para {user_id}: {e}")

    @staticmethod
    async def remap_cpf_to_new_user(new_user_id: int, old_user_id: int, cpf: str, new_username: str) -> bool:
        """Remapeia um CPF para um novo usuário, removendo o antigo."""
        from src.sentinela.clients.db_client import update_user_id_for_cpf

        try:
            logger.info(f"Iniciando remapeamento de CPF {cpf}. Novo dono: {new_user_id}, antigo: {old_user_id}")

            # 1. Remove o usuário antigo do grupo
            reason = f"CPF associado a uma nova conta Telegram (@{new_username})"
            await remove_user_from_group(old_user_id, reason)

            # 2. Atualiza o banco de dados para o novo usuário
            update_user_id_for_cpf(cpf, new_user_id, new_username)

            # 3. Completa a verificação para o novo usuário
            CPFVerificationService.complete_verification(new_user_id, True, cpf)
            
            logger.info(f"CPF {cpf} remapeado com sucesso para o usuário {new_user_id}")
            return True

        except Exception as e:
            logger.error(f"Erro crítico ao remapear CPF {cpf} para o usuário {new_user_id}: {e}")
            return False

    @staticmethod
    def get_verification_stats() -> dict:
        """Retorna estatísticas de verificações"""
        try:
            with get_db_connection() as conn:
                # Verificações pendentes
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM pending_cpf_verifications
                    WHERE status = 'pending'
                """)
                pending_count = cursor.fetchone()[0]

                # Verificações expiradas
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM pending_cpf_verifications
                    WHERE status = 'pending' AND expires_at < CURRENT_TIMESTAMP
                """)
                expired_count = cursor.fetchone()[0]

                # Histórico últimas 24h
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                    FROM cpf_verification_history
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                history_24h = cursor.fetchone()

                return {
                    'pending': pending_count,
                    'expired': expired_count,
                    'last_24h': {
                        'total': history_24h[0],
                        'successful': history_24h[1] or 0,
                        'failed': history_24h[2] or 0
                    }
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de verificação: {e}")
            return {
                'pending': 0,
                'expired': 0,
                'last_24h': {'total': 0, 'successful': 0, 'failed': 0}
            }