"""
Command Handlers para operações de verificação de CPF.

Implementa a lógica de aplicação para comandos
relacionados à verificação de CPF.
"""

import logging
from typing import Dict, Any, List

from .base import CommandHandler, CommandResult
from ..commands.cpf_verification_commands import (
    StartCPFVerificationCommand,
    SubmitCPFForVerificationCommand,
    CancelCPFVerificationCommand,
    ProcessExpiredVerificationsCommand,
    GetVerificationStatsCommand,
    ResolveCPFDuplicateCommand
)
from ...domain.entities.cpf_verification import (
    CPFVerificationRequest,
    VerificationId,
    VerificationType,
    VerificationStatus
)
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.identifiers import UserId
from ...domain.value_objects.cpf import CPF
from ...domain.services.cpf_validation_service import CPFValidationService
from ...domain.services.duplicate_cpf_service import DuplicateCPFService
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class StartCPFVerificationHandler(CommandHandler[StartCPFVerificationCommand]):
    """Handler para iniciar verificação de CPF."""

    def __init__(
        self,
        verification_repository: CPFVerificationRepository,
        user_repository: UserRepository,
        event_bus: EventBus
    ):
        self.verification_repository = verification_repository
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def handle(self, command: StartCPFVerificationCommand) -> CommandResult:
        """
        Inicia uma nova verificação de CPF.

        Args:
            command: Comando com dados da verificação

        Returns:
            CommandResult: Resultado da operação
        """
        try:
            user_id = UserId(command.user_id)

            # NOTA: Removida validação de usuário existente no UserRepository
            # Novos membros podem iniciar verificação antes de terem um User criado
            # O User será criado no UserRepository após CPF validado com sucesso

            # Verifica se já existe verificação pendente
            existing = await self.verification_repository.find_pending_by_user(user_id.value)
            if existing:
                return CommandResult.failure(
                    "verification_already_pending",
                    "Já existe uma verificação pendente para este usuário",
                    {"verification_id": str(existing.id)}
                )

            # Valida tipo de verificação
            try:
                verification_type = VerificationType(command.verification_type)
            except ValueError:
                return CommandResult.failure(
                    "invalid_verification_type",
                    f"Tipo de verificação inválido: {command.verification_type}"
                )

            # Cria nova verificação
            verification_id = VerificationId.generate()

            # Garante que user_mention não seja nulo, usando username como fallback
            user_mention = command.user_mention or command.username

            verification = CPFVerificationRequest(
                verification_id=verification_id,
                user_id=user_id,
                username=command.username,
                user_mention=user_mention,
                verification_type=verification_type,
                source_action=command.source_action
            )

            # Salva no repository
            await self.verification_repository.save(verification)

            # Publica eventos de domínio
            for event in verification.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Verificação iniciada para usuário {command.username} (ID: {command.user_id})")

            return CommandResult.success({
                "verification_id": str(verification_id),
                "verification_type": verification_type.value,
                "expires_at": verification.expires_at.isoformat(),
                "message": "Verificação iniciada com sucesso"
            })

        except Exception as e:
            logger.error(f"Erro ao iniciar verificação para usuário {command.user_id}: {e}")
            return CommandResult.failure(
                "system_error",
                "Erro interno do sistema",
                {"error": str(e)}
            )


class SubmitCPFForVerificationHandler(CommandHandler[SubmitCPFForVerificationCommand]):
    """Handler para submeter CPF para verificação."""

    def __init__(
        self,
        verification_repository: CPFVerificationRepository,
        user_repository: UserRepository,
        cpf_validation_service: CPFValidationService,
        duplicate_cpf_service: DuplicateCPFService,
        event_bus: EventBus
    ):
        self.verification_repository = verification_repository
        self.user_repository = user_repository
        self.cpf_validation_service = cpf_validation_service
        self.duplicate_cpf_service = duplicate_cpf_service
        self.event_bus = event_bus

    async def handle(self, command: SubmitCPFForVerificationCommand) -> CommandResult:
        """
        Processa submissão de CPF para verificação.

        Args:
            command: Comando com CPF fornecido

        Returns:
            CommandResult: Resultado da verificação
        """
        try:
            # Converte user_id para UserId (repository agora aceita)
            user_id = UserId(command.user_id)
            cpf_masked = f"{command.cpf[:3]}***{command.cpf[-2:]}" if len(command.cpf) >= 5 else "***"

            logger.info(f"[CPF Handler] Iniciando verificação - User: {user_id.value}, CPF: {cpf_masked}")

            # Busca verificação pendente
            verification = await self.verification_repository.find_pending_by_user(user_id)
            if not verification:
                logger.warning(f"[CPF Handler] ❌ Nenhuma verificação pendente para usuário {user_id.value}")
                return CommandResult.failure(
                    "no_pending_verification",
                    "Não há verificação pendente para este usuário"
                )

            logger.info(f"[CPF Handler] Verificação encontrada - ID: {verification.id}, Status: {verification.status.value}")

            # Verifica se ainda pode fazer tentativas
            if not verification.can_attempt():
                logger.warning(f"[CPF Handler] ❌ Usuário {user_id} não pode mais tentar - Tentativas: {verification.attempt_count}, Status: {verification.status.value}")
                return CommandResult.failure(
                    "cannot_attempt",
                    "Não é possível fazer mais tentativas de verificação",
                    {
                        "attempts_made": verification.attempt_count,
                        "status": verification.status.value,
                        "is_expired": verification.is_expired()
                    }
                )

            # Valida formato do CPF
            logger.info(f"[CPF Handler] Validando formato do CPF {cpf_masked}")
            from ...domain.services.cpf_validation_service import CPFValidationService
            is_valid_cpf = CPFValidationService.validate_cpf(command.cpf)
            if not is_valid_cpf:
                logger.warning(f"[CPF Handler] ❌ CPF inválido {cpf_masked}: formato inválido")
                verification.add_attempt(
                    cpf_provided=command.cpf, success=False, failure_reason="invalid_cpf_format"
                )
                await self.verification_repository.save(verification)
                return CommandResult.failure(
                    "invalid_cpf_format", "CPF com formato inválido", {"attempts_left": verification.has_attempts_left()}
                )

            cpf = CPF.from_raw(command.cpf)
            logger.info(f"[CPF Handler] ✅ CPF válido {cpf_masked}")

            # --- LÓGICA REORDENADA ---
            # 1. Verifica no sistema externo (HubSoft) PRIMEIRO
            logger.info(f"[CPF Handler] Consultando HubSoft para {cpf_masked}")
            client_data = await self._verify_cpf_in_hubsoft(cpf)
            if not client_data:
                logger.warning(f"[CPF Handler] ❌ CPF {cpf_masked} não encontrado no HubSoft ou sem serviço ativo")
                verification.add_attempt(
                    cpf_provided=str(cpf), success=False, failure_reason="cpf_not_found_in_hubsoft"
                )
                await self.verification_repository.save(verification)
                return CommandResult.failure(
                    "cpf_not_found",
                    "CPF não encontrado em nossa base de clientes ativos",
                    {"attempts_left": verification.has_attempts_left()}
                )
            
            logger.info(f"[CPF Handler] ✅ Cliente encontrado no HubSoft: {client_data.get('nome_razaosocial', 'N/A')}")

            # 2. Se o contrato está ativo, AGORA verifica duplicidade
            logger.info(f"[CPF Handler] Verificando duplicidade para {cpf_masked}")
            duplicate_result = await self.duplicate_cpf_service.check_for_duplicates(
                cpf_hash=cpf.value, exclude_user_id=user_id.value
            )

            if duplicate_result["has_duplicates"]:
                logger.warning(f"[CPF Handler] ❌ Conflito de CPF duplicado detectado para {cpf_masked}: {duplicate_result}")
                # Retorna um resultado de sucesso, mas com um status de conflito,
                # para que a camada de apresentação possa iniciar o fluxo interativo.
                return CommandResult.success(
                    {
                        "status": "conflict_detected",
                        "conflict_details": duplicate_result,
                        "message": "CPF duplicado detectado, aguardando resolução do usuário."
                    }
                )

            logger.info(f"[CPF Handler] ✅ Sem duplicidade para {cpf_masked}")
            # --- FIM DA LÓGICA REORDENADA ---

            # Caminho feliz: Contrato ativo e sem duplicatas
            verification.add_attempt(cpf_provided=str(cpf), success=True)
            verification.complete_with_success(cpf, client_data)
            await self.verification_repository.save(verification)

            for event in verification.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"[CPF Handler] ✅✅✅ CPF verificado com sucesso para usuário {command.username} - CPF: {cpf_masked}")

            return CommandResult.success({
                "verification_id": str(verification.id),
                "cpf_verified": True,
                "client_data": client_data,
                "message": "CPF verificado com sucesso! Seus dados foram atualizados."
            })

        except Exception as e:
            logger.error(f"Erro ao verificar CPF para usuário {command.user_id}: {e}")
            return CommandResult.failure(
                "system_error",
                "Erro interno do sistema",
                {"error": str(e)}
            )

    async def _verify_cpf_in_hubsoft(self, cpf: CPF) -> Dict[str, Any]:
        """
        Verifica CPF no sistema HubSoft.

        Aceita QUALQUER cliente com serviço ativo, independente do plano.

        Args:
            cpf: CPF a ser verificado

        Returns:
            Dict[str, Any]: Dados do cliente ou None se não encontrado/ativo
        """
        try:
            # Importa dinamicamente para evitar dependência circular
            from ....integrations.hubsoft.cliente import get_client_info

            # Log para debug
            cpf_masked = f"{str(cpf)[:3]}***{str(cpf)[-2:]}"
            logger.info(f"Consultando HubSoft para CPF {cpf_masked}")

            # Usa função otimizada (não deprecated)
            client_data = get_client_info(str(cpf), full_data=True)

            if client_data:
                # Campo correto retornado pela API HubSoft
                client_name = client_data.get('nome_razaosocial',
                                              client_data.get('nome',
                                              client_data.get('client_name', 'N/A')))

                # Verifica se tem serviço ativo
                servico_status = client_data.get('servico_status', '')
                servico_nome = client_data.get('servico_nome', 'N/A')

                logger.info(f"✅ Cliente encontrado no HubSoft: {client_name}")
                logger.info(f"   Serviço: {servico_nome}")
                logger.info(f"   Status: {servico_status}")
                logger.debug(f"Dados retornados do HubSoft: {list(client_data.keys())}")

                # Valida se serviço está ativo
                # API já filtra por "servico_habilitado", mas validamos novamente
                if not servico_status or 'habilitado' not in servico_status.lower():
                    logger.warning(f"❌ Cliente {client_name} sem serviço habilitado: {servico_status}")
                    return None

                logger.info(f"✅ Cliente {client_name} validado com sucesso - Serviço ativo")
                return client_data
            else:
                logger.warning(f"❌ Nenhum cliente encontrado no HubSoft para CPF {cpf_masked}")
                return None

        except Exception as e:
            logger.error(f"Erro ao verificar CPF no HubSoft: {e}", exc_info=True)
            return None


class CancelCPFVerificationHandler(CommandHandler[CancelCPFVerificationCommand]):
    """Handler para cancelar verificação de CPF."""

    def __init__(
        self,
        verification_repository: CPFVerificationRepository,
        event_bus: EventBus
    ):
        self.verification_repository = verification_repository
        self.event_bus = event_bus

    async def handle(self, command: CancelCPFVerificationCommand) -> CommandResult:
        """
        Cancela uma verificação de CPF.

        Args:
            command: Comando com dados do cancelamento

        Returns:
            CommandResult: Resultado da operação
        """
        try:
            user_id = UserId(command.user_id)

            # Busca verificação pendente
            verification = await self.verification_repository.find_pending_by_user(user_id.value)
            if not verification:
                return CommandResult.failure(
                    "no_pending_verification",
                    "Não há verificação pendente para cancelar"
                )

            # Cancela verificação
            verification.cancel_verification(command.reason)

            # Salva alterações
            await self.verification_repository.save(verification)

            # Publica eventos
            for event in verification.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Verificação cancelada para usuário {command.username}")

            return CommandResult.success({
                "verification_id": str(verification.id),
                "cancelled": True,
                "reason": command.reason,
                "message": "Verificação cancelada com sucesso"
            })

        except Exception as e:
            logger.error(f"Erro ao cancelar verificação para usuário {command.user_id}: {e}")
            return CommandResult.failure(
                "system_error",
                "Erro interno do sistema",
                {"error": str(e)}
            )


class ResolveCPFDuplicateHandler(CommandHandler[ResolveCPFDuplicateCommand]):
    """Handler para resolver conflitos de CPF duplicado."""

    def __init__(
        self,
        duplicate_cpf_service: DuplicateCPFService,
        verification_repository: CPFVerificationRepository,
        event_bus: EventBus
    ):
        self.duplicate_cpf_service = duplicate_cpf_service
        self.verification_repository = verification_repository
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
                return CommandResult.failure("verification_not_found", "Verificação original não encontrada.")

            last_attempt = verification.get_last_attempt()
            if not last_attempt or not last_attempt.cpf_provided:
                 return CommandResult.failure("cpf_not_found_in_attempt", "CPF não encontrado na tentativa de verificação.")
            
            cpf = CPF.from_raw(last_attempt.cpf_provided)

            from ....integrations.hubsoft.cliente import get_client_info
            client_data = get_client_info(str(cpf), full_data=True)
            if not client_data:
                 return CommandResult.failure("client_not_found_after_resolution", "Cliente não encontrado no Hubsoft após resolução.")

            verification.complete_with_success(cpf, client_data)
            await self.verification_repository.save(verification)

            for event in verification.get_domain_events():
                await self.event_bus.publish(event)

            logger.info(f"Conflito resolvido e verificação {command.verification_id} completada.")
            
            return CommandResult.success({
                "message": "Conflito resolvido e verificação completada.",
                "client_data": client_data,
                "verified": True
            })

        except Exception as e:
            logger.error(f"Erro crítico ao resolver duplicata para verificação {command.verification_id}: {e}", exc_info=True)
            return CommandResult.failure("system_error", "Erro interno do sistema ao resolver duplicata.")


# NOTE: ProcessExpiredVerificationsHandler foi movido para arquivo standalone
# Ver: application/command_handlers/process_expired_verifications_handler.py
# Esta classe estava duplicada aqui e foi removida para evitar confusão.


class GetVerificationStatsHandler(CommandHandler[GetVerificationStatsCommand]):
    """Handler para obter estatísticas de verificação."""

    def __init__(self, verification_repository: CPFVerificationRepository):
        self.verification_repository = verification_repository

    async def handle(self, command: GetVerificationStatsCommand) -> CommandResult:
        """
        Obtém estatísticas de verificação.

        Args:
            command: Comando com parâmetros

        Returns:
            CommandResult: Estatísticas de verificação
        """
        try:
            # Busca estatísticas básicas
            stats = await self.verification_repository.get_verification_stats()

            # Se solicitado, inclui detalhes granulares
            if command.include_details:
                recent_verifications = await self.verification_repository.find_recent_verifications(24)
                stats["recent_verifications"] = [
                    {
                        "verification_id": str(v.id),
                        "user_id": v.user_id.value,
                        "username": v.username,
                        "type": v.verification_type.value,
                        "status": v.status.value,
                        "attempt_count": v.attempt_count,
                        "created_at": v.created_at.isoformat(),
                        "expires_at": v.expires_at.isoformat(),
                        "completed_at": v.completed_at.isoformat() if v.completed_at else None
                    }
                    for v in recent_verifications
                ]

            return CommandResult.success(stats)

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de verificação: {e}")
            return CommandResult.failure(
                "system_error",
                "Erro interno do sistema",
                {"error": str(e)}
            )