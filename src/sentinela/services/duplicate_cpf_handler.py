"""
DuplicateCPFHandler - Serviço para tratamento de CPF duplicado

Este serviço gerencia todo o fluxo de detecção e resolução de conflitos
quando um CPF já está sendo usado por outro usuário do Telegram.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.error import TelegramError

from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID
from src.sentinela.clients.db_client import get_user_by_cpf, save_user_data, get_db_connection
from src.sentinela.services.group_service import remove_user_from_group
from src.sentinela.services.cpf_validation_service import CPFValidationService

logger = logging.getLogger(__name__)

class DuplicateCPFHandler:
    """Gerenciador de conflitos de CPF duplicado"""

    def __init__(self):
        self._pending_confirmations = {}  # Cache de confirmações pendentes

    def detect_duplicate_cpf(self, cpf: str, current_user_id: int) -> Optional[Dict]:
        """
        Detecta se um CPF já está em uso por outro usuário

        Args:
            cpf: CPF a ser verificado
            current_user_id: ID do usuário atual

        Returns:
            Optional[Dict]: Dados do usuário que já usa o CPF, ou None se não há conflito
        """
        clean_cpf = CPFValidationService.clean_cpf(cpf)
        existing_user = get_user_by_cpf(clean_cpf)

        if existing_user and existing_user['user_id'] != current_user_id:
            logger.warning(
                f"CPF duplicado detectado: {CPFValidationService.mask_cpf(clean_cpf)} "
                f"já usado por user_id {existing_user['user_id']}, "
                f"novo usuário: {current_user_id}"
            )
            return existing_user

        return None

    async def handle_duplicate_cpf_conflict(
        self,
        cpf: str,
        new_user_id: int,
        new_username: str,
        existing_user: Dict
    ) -> Dict:
        """
        Inicia o processo de resolução de conflito de CPF duplicado

        Args:
            cpf: CPF em conflito
            new_user_id: ID do novo usuário
            new_username: Username do novo usuário
            existing_user: Dados do usuário existente

        Returns:
            Dict: Resultado da operação
        """
        try:
            # Cria entrada de confirmação pendente
            confirmation_id = f"{new_user_id}_{existing_user['user_id']}_{int(datetime.now().timestamp())}"

            self._pending_confirmations[confirmation_id] = {
                'cpf': cpf,
                'new_user_id': new_user_id,
                'new_username': new_username,
                'existing_user': existing_user,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=10)  # 10 minutos para decidir
            }

            # Envia mensagem de confirmação
            await self._send_duplicate_cpf_confirmation(confirmation_id)

            return {
                'success': False,
                'reason': 'duplicate_cpf_confirmation_sent',
                'message': (
                    f"🔄 <b>CPF já está em uso</b>\n\n"
                    f"O CPF <code>{CPFValidationService.mask_cpf(cpf)}</code> já está "
                    f"vinculado à conta de <b>{existing_user['client_name']}</b>.\n\n"
                    f"📱 <b>Verifique suas mensagens privadas</b> para escolher qual "
                    f"conta deve ficar vinculada a este CPF.\n\n"
                    f"⏰ Você tem <b>10 minutos</b> para decidir."
                ),
                'confirmation_id': confirmation_id
            }

        except Exception as e:
            logger.error(f"Erro ao lidar com CPF duplicado: {e}")
            return {
                'success': False,
                'reason': 'duplicate_cpf_error',
                'message': "❌ Erro interno ao processar CPF duplicado. Tente novamente."
            }

    async def _send_duplicate_cpf_confirmation(self, confirmation_id: str):
        """Envia mensagem de confirmação para escolha da conta"""
        confirmation = self._pending_confirmations.get(confirmation_id)
        if not confirmation:
            return

        new_user_id = confirmation['new_user_id']
        existing_user = confirmation['existing_user']
        cpf_masked = CPFValidationService.mask_cpf(confirmation['cpf'])

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔄 Usar esta conta (atual)",
                    callback_data=f"cpf_duplicate_keep_new_{confirmation_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"📱 Manter conta anterior ({existing_user['client_name']})",
                    callback_data=f"cpf_duplicate_keep_old_{confirmation_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancelar",
                    callback_data=f"cpf_duplicate_cancel_{confirmation_id}"
                )
            ]
        ])

        message = (
            f"🔄 <b>Conflito de CPF Detectado</b>\n\n"
            f"O CPF <code>{cpf_masked}</code> já está sendo usado por:\n"
            f"👤 <b>{existing_user['client_name']}</b>\n\n"
            f"<b>Qual conta deve ficar vinculada a este CPF?</b>\n\n"
            f"🔄 <b>Esta conta:</b> Sua conta atual será vinculada ao CPF "
            f"e a conta anterior será removida do grupo.\n\n"
            f"📱 <b>Conta anterior:</b> Mantém a vinculação existente "
            f"e sua solicitação será cancelada.\n\n"
            f"⏰ <i>Esta decisão expira em 10 minutos.</i>"
        )

        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(
                chat_id=new_user_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            logger.info(f"Mensagem de confirmação de CPF duplicado enviada para {new_user_id}")

        except TelegramError as e:
            logger.error(f"Erro ao enviar mensagem de confirmação: {e}")
            # Remove da lista de pendentes se não conseguiu enviar
            self._pending_confirmations.pop(confirmation_id, None)

    async def process_duplicate_cpf_decision(self, confirmation_id: str, decision: str) -> Dict:
        """
        Processa a decisão do usuário sobre o CPF duplicado

        Args:
            confirmation_id: ID da confirmação
            decision: Decisão ('keep_new', 'keep_old', 'cancel')

        Returns:
            Dict: Resultado da operação
        """
        confirmation = self._pending_confirmations.get(confirmation_id)
        if not confirmation:
            return {
                'success': False,
                'message': "❌ Confirmação não encontrada ou expirada."
            }

        # Verifica se não expirou
        if datetime.now() > confirmation['expires_at']:
            self._pending_confirmations.pop(confirmation_id, None)
            return {
                'success': False,
                'message': "⏰ Tempo esgotado para decisão. Tente o processo novamente."
            }

        try:
            if decision == 'keep_new':
                return await self._handle_keep_new_account(confirmation)
            elif decision == 'keep_old':
                return await self._handle_keep_old_account(confirmation)
            elif decision == 'cancel':
                return await self._handle_cancel_decision(confirmation)
            else:
                return {
                    'success': False,
                    'message': "❌ Decisão inválida."
                }

        except Exception as e:
            logger.error(f"Erro ao processar decisão de CPF duplicado: {e}")
            return {
                'success': False,
                'message': "❌ Erro interno ao processar decisão. Tente novamente."
            }
        finally:
            # Remove da lista de pendentes
            self._pending_confirmations.pop(confirmation_id, None)

    async def _handle_keep_new_account(self, confirmation: Dict) -> Dict:
        """Processa decisão de manter a nova conta"""
        new_user_id = confirmation['new_user_id']
        new_username = confirmation['new_username']
        existing_user = confirmation['existing_user']
        cpf = confirmation['cpf']

        logger.info(
            f"Processando troca de CPF: removendo user_id {existing_user['user_id']} "
            f"e vinculando ao user_id {new_user_id}"
        )

        try:
            # Remove usuário antigo do grupo
            removal_success = await remove_user_from_group(
                existing_user['user_id'],
                f"CPF {CPFValidationService.mask_cpf(cpf)} transferido para nova conta"
            )

            if removal_success:
                logger.info(f"Usuário {existing_user['user_id']} removido do grupo com sucesso")
            else:
                logger.warning(f"Falha ao remover usuário {existing_user['user_id']} do grupo")

            # Atualiza o mapeamento no banco de dados
            # Note: Precisa dos dados do cliente da API para salvar completo
            from src.sentinela.integrations.hubsoft.cliente import get_client_data

            client_data = get_client_data(cpf)
            if not client_data:
                return {
                    'success': False,
                    'message': "❌ Erro ao buscar dados do cliente. CPF pode estar inativo."
                }

            # Salva dados da nova conta
            save_success = save_user_data(new_user_id, new_username, cpf, client_data)

            if save_success:
                return {
                    'success': True,
                    'message': (
                        f"✅ <b>CPF vinculado com sucesso!</b>\n\n"
                        f"🔄 Sua conta agora está vinculada ao CPF "
                        f"<code>{CPFValidationService.mask_cpf(cpf)}</code>.\n\n"
                        f"📱 A conta anterior foi removida do grupo.\n\n"
                        f"🎮 Você já pode usar todos os recursos do bot!"
                    )
                }
            else:
                return {
                    'success': False,
                    'message': "❌ Erro ao salvar novos dados. Tente novamente."
                }

        except Exception as e:
            logger.error(f"Erro ao processar manter nova conta: {e}")
            return {
                'success': False,
                'message': "❌ Erro interno durante a troca. Contate o suporte."
            }

    async def _handle_keep_old_account(self, confirmation: Dict) -> Dict:
        """Processa decisão de manter a conta antiga"""
        existing_user = confirmation['existing_user']
        cpf = confirmation['cpf']

        logger.info(f"Usuário optou por manter conta existente para CPF {CPFValidationService.mask_cpf(cpf)}")

        return {
            'success': False,
            'reason': 'kept_existing_account',
            'message': (
                f"✅ <b>Conta anterior mantida</b>\n\n"
                f"O CPF <code>{CPFValidationService.mask_cpf(cpf)}</code> continua "
                f"vinculado à conta de <b>{existing_user['client_name']}</b>.\n\n"
                f"❌ Sua solicitação foi cancelada.\n\n"
                f"💡 Se precisar de ajuda, entre em contato com o suporte."
            )
        }

    async def _handle_cancel_decision(self, confirmation: Dict) -> Dict:
        """Processa cancelamento da decisão"""
        cpf = confirmation['cpf']

        logger.info(f"Usuário cancelou decisão de CPF duplicado para {CPFValidationService.mask_cpf(cpf)}")

        return {
            'success': False,
            'reason': 'cancelled_by_user',
            'message': (
                f"❌ <b>Operação cancelada</b>\n\n"
                f"A verificação do CPF <code>{CPFValidationService.mask_cpf(cpf)}</code> "
                f"foi cancelada.\n\n"
                f"💡 Você pode tentar novamente a qualquer momento usando /start."
            )
        }

    def cleanup_expired_confirmations(self):
        """Remove confirmações expiradas"""
        now = datetime.now()
        expired_ids = [
            conf_id for conf_id, conf in self._pending_confirmations.items()
            if now > conf['expires_at']
        ]

        for conf_id in expired_ids:
            self._pending_confirmations.pop(conf_id, None)
            logger.debug(f"Confirmação expirada removida: {conf_id}")

        if expired_ids:
            logger.info(f"Removidas {len(expired_ids)} confirmações expiradas")

    def get_pending_confirmation(self, confirmation_id: str) -> Optional[Dict]:
        """Retorna dados de uma confirmação pendente"""
        return self._pending_confirmations.get(confirmation_id)

    def get_stats(self) -> Dict:
        """Retorna estatísticas do handler"""
        now = datetime.now()
        active_confirmations = sum(
            1 for conf in self._pending_confirmations.values()
            if now <= conf['expires_at']
        )

        return {
            'total_pending': len(self._pending_confirmations),
            'active_confirmations': active_confirmations,
            'expired_confirmations': len(self._pending_confirmations) - active_confirmations
        }


# Instância global do handler
duplicate_cpf_handler = DuplicateCPFHandler()