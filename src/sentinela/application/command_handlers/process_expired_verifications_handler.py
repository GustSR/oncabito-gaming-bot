"""
Process Expired Verifications Handler.

Handler para processar verificações de CPF expiradas.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from ..commands.cpf_verification_commands import ProcessExpiredVerificationsCommand
from .base import CommandHandler
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.entities.cpf_verification import VerificationStatus
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ProcessExpiredVerificationsHandler(CommandHandler[ProcessExpiredVerificationsCommand]):
    """Handler para processar verificações expiradas."""

    def __init__(
        self,
        verification_repository: CPFVerificationRepository,
        event_bus: EventBus
    ):
        self.verification_repository = verification_repository
        self.event_bus = event_bus

    async def handle(self, command: ProcessExpiredVerificationsCommand) -> Dict[str, Any]:
        """
        Processa verificações expiradas.

        Args:
            command: Comando para processar verificações expiradas

        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info("Iniciando processamento de verificações expiradas")

            # Busca verificações expiradas
            expired_verifications = await self.verification_repository.find_expired_verifications()

            processed_count = 0
            error_count = 0

            for verification in expired_verifications:
                try:
                    # Atualiza status para expirado
                    verification.status = VerificationStatus.EXPIRED
                    verification.completed_at = datetime.now()

                    # Salva no repositório
                    await self.verification_repository.save(verification)

                    processed_count += 1
                    logger.debug(f"Verificação {verification.id.value} marcada como expirada")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Erro ao processar verificação {verification.id.value}: {e}")

            # Faz limpeza de verificações muito antigas
            cleanup_count = await self.verification_repository.cleanup_old_verifications(
                days_old=command.cleanup_days_old
            )

            result = {
                "success": True,
                "processed_count": processed_count,
                "error_count": error_count,
                "cleanup_count": cleanup_count,
                "total_found": len(expired_verifications)
            }

            logger.info(f"Processamento concluído: {result}")
            return result

        except Exception as e:
            error_msg = f"Erro ao processar verificações expiradas: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "processed_count": 0,
                "error_count": 0,
                "cleanup_count": 0
            }