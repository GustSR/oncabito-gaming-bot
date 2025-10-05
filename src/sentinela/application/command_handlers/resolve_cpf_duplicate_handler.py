
import logging
from .base import CommandHandler, CommandResult
from ..commands.cpf_verification_commands import ResolveCPFDuplicateCommand
from ...domain.services.duplicate_cpf_service import DuplicateCPFService
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.repositories.user_repository import UserRepository
from ...domain.entities.cpf_verification import VerificationId
from ...domain.value_objects.cpf import CPF
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)

class ResolveCPFDuplicateHandler(CommandHandler[ResolveCPFDuplicateCommand]):
    """Handler para resolver conflitos de CPF duplicado."""

    def __init__(
        self,
        duplicate_cpf_service: DuplicateCPFService,
        verification_repository: CPFVerificationRepository,
        user_repository: UserRepository,
        event_bus: EventBus
    ):
        self.duplicate_cpf_service = duplicate_cpf_service
        self.verification_repository = verification_repository
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def handle(self, command: ResolveCPFDuplicateCommand) -> CommandResult:
        try:
            logger.info(f"Resolvendo conflito de CPF para verificação {command.verification_id}")

            resolution_result = await self.duplicate_cpf_service.resolve_duplicate(
                primary_user_id=command.primary_user_id,
                duplicate_user_ids=command.duplicate_user_ids,
                resolution_type="merge"
            )

            if not resolution_result.get("success"):
                return CommandResult.failure(
                    "resolution_failed",
                    resolution_result.get("error", "Falha ao resolver duplicata."),
                    resolution_result.get("error_details", {})
                )

            verification = await self.verification_repository.find_by_id(VerificationId(command.verification_id))
            if not verification:
                return CommandResult.failure("verification_not_found", "Verificação original não encontrada após resolução de duplicata.")

            last_attempt = verification.get_last_attempt()
            if not last_attempt or not last_attempt.cpf_provided:
                 return CommandResult.failure("cpf_not_found_in_attempt", "Não foi possível encontrar o CPF na tentativa de verificação.")
            
            cpf = CPF.from_raw(last_attempt.cpf_provided)

            from ....integrations.hubsoft.cliente import get_client_info
            client_data = get_client_info(str(cpf), full_data=True)
            if not client_data:
                 return CommandResult.failure("client_not_found_after_resolution", "Cliente não encontrado no Hubsoft após resolução.")

            verification.complete_with_success(cpf, client_data)
            await self.verification_repository.save(verification)

            for event in verification.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Conflito resolvido e verificação {command.verification_id} completada com sucesso.")
            
            return CommandResult.success({
                "message": "Conflito resolvido e verificação completada.",
                "client_data": client_data,
                "verified": True
            })

        except Exception as e:
            logger.error(f"Erro crítico ao resolver duplicata para verificação {command.verification_id}: {e}", exc_info=True)
            return CommandResult.failure("system_error", "Erro interno do sistema ao resolver duplicata.")
