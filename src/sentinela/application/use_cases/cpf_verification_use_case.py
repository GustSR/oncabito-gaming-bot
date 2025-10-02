"""
Use Case para operações de verificação de CPF.

Coordena o fluxo completo de verificação de CPF,
incluindo validação, duplicidade e integração com sistemas externos.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base import UseCase, UseCaseResult
from ..commands.cpf_verification_commands import (
    StartCPFVerificationCommand,
    SubmitCPFForVerificationCommand,
    CancelCPFVerificationCommand,
    ProcessExpiredVerificationsCommand
)
from ..command_handlers.cpf_verification_handlers import (
    StartCPFVerificationHandler,
    SubmitCPFForVerificationHandler,
    CancelCPFVerificationHandler,
    ProcessExpiredVerificationsHandler
)
from ...domain.entities.cpf_verification import VerificationType, VerificationStatus
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.value_objects.identifiers import UserId

logger = logging.getLogger(__name__)


@dataclass
class CPFVerificationResult:
    """
    Resultado de uma operação de verificação de CPF.

    Attributes:
        success: Se a operação foi bem-sucedida
        verification_id: ID da verificação (se aplicável)
        message: Mensagem para o usuário
        status: Status atual da verificação
        data: Dados adicionais da verificação
        error_code: Código de erro (se aplicável)
        next_action: Próxima ação sugerida
    """
    success: bool
    message: str
    verification_id: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    next_action: Optional[str] = None


class CPFVerificationUseCase(UseCase):
    """
    Use Case para coordenar operações de verificação de CPF.

    Responsável por orquestrar todo o fluxo de verificação,
    desde a criação até a conclusão ou cancelamento.
    """

    def __init__(
        self,
        start_handler: StartCPFVerificationHandler,
        submit_handler: SubmitCPFForVerificationHandler,
        cancel_handler: CancelCPFVerificationHandler,
        expire_handler: ProcessExpiredVerificationsHandler,
        verification_repository: CPFVerificationRepository
    ):
        self.start_handler = start_handler
        self.submit_handler = submit_handler
        self.cancel_handler = cancel_handler
        self.expire_handler = expire_handler
        self.verification_repository = verification_repository

    async def start_verification(
        self,
        user_id: int,
        username: str,
        user_mention: str,
        verification_type: str = "auto_checkup",
        source_action: Optional[str] = None
    ) -> CPFVerificationResult:
        """
        Inicia uma nova verificação de CPF.

        Args:
            user_id: ID do usuário no Telegram
            username: Nome de usuário
            user_mention: Mention formatado
            verification_type: Tipo de verificação
            source_action: Ação que originou a verificação

        Returns:
            CPFVerificationResult: Resultado da operação
        """
        try:
            logger.info(f"Iniciando verificação de CPF para usuário {username} (ID: {user_id})")

            # Valida parâmetros
            if not self._validate_user_data(user_id, username):
                return CPFVerificationResult(
                    success=False,
                    message="Dados de usuário inválidos",
                    error_code="invalid_user_data",
                    next_action="check_user_registration"
                )

            # Verifica rate limiting
            rate_limit_result = await self._check_rate_limiting(user_id)
            if not rate_limit_result.allowed:
                return CPFVerificationResult(
                    success=False,
                    message=rate_limit_result.message,
                    error_code="rate_limited",
                    next_action="wait_before_retry",
                    data={"retry_after": rate_limit_result.retry_after}
                )

            # Executa comando
            command = StartCPFVerificationCommand(
                user_id=user_id,
                username=username,
                user_mention=user_mention,
                verification_type=verification_type,
                source_action=source_action
            )

            result = await self.start_handler.handle(command)

            if result.success:
                return CPFVerificationResult(
                    success=True,
                    verification_id=result.data.get("verification_id"),
                    message=result.data.get("message", "Verificação iniciada com sucesso"),
                    status="pending",
                    data={
                        "verification_type": verification_type,
                        "expires_at": result.data.get("expires_at"),
                        "max_attempts": 3
                    },
                    next_action="provide_cpf"
                )
            else:
                return CPFVerificationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code,
                    next_action=self._get_next_action_for_error(result.error_code)
                )

        except Exception as e:
            logger.error(f"Erro ao iniciar verificação para usuário {user_id}: {e}")
            return CPFVerificationResult(
                success=False,
                message="Erro interno do sistema. Tente novamente mais tarde.",
                error_code="system_error",
                next_action="retry_later"
            )

    async def submit_cpf(
        self,
        user_id: int,
        username: str,
        cpf: str
    ) -> CPFVerificationResult:
        """
        Submete um CPF para verificação.

        Args:
            user_id: ID do usuário
            username: Nome de usuário
            cpf: CPF fornecido

        Returns:
            CPFVerificationResult: Resultado da verificação
        """
        try:
            logger.info(f"Processando CPF para usuário {username} (ID: {user_id})")
            logger.info(f"CPF recebido (primeiros 3 dígitos): {cpf[:3]}***")

            # Sanitiza CPF
            clean_cpf = self._sanitize_cpf(cpf)
            logger.info(f"CPF sanitizado (tamanho: {len(clean_cpf)}, primeiros 3: {clean_cpf[:3]}***)")

            # Executa comando
            command = SubmitCPFForVerificationCommand(
                user_id=user_id,
                username=username,
                cpf=clean_cpf
            )

            result = await self.submit_handler.handle(command)
            logger.info(f"Handler result - success: {result.success}, has_data: {result.data is not None}")

            if result.success:
                # Proteção contra result.data None
                if not result.data:
                    logger.error(f"Handler retornou success=True mas data=None para usuário {user_id}")
                    return CPFVerificationResult(
                        success=False,
                        message="Erro interno ao processar CPF. Tente novamente.",
                        error_code="invalid_handler_response",
                        next_action="retry_later"
                    )

                return CPFVerificationResult(
                    success=True,
                    verification_id=result.data.get("verification_id"),
                    message=result.data.get("message", "CPF verificado com sucesso!"),
                    status="completed",
                    data={
                        "verified": True,
                        "client_data": result.data.get("client_data", {})
                    },
                    next_action="verification_complete"
                )
            else:
                # Busca dados atualizados da verificação para próximos passos
                verification_data = await self._get_verification_context(user_id)

                # Proteção contra result.data None no failure
                result_data = result.data if result.data else {}

                return CPFVerificationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code,
                    status=verification_data.get("status"),
                    data={
                        "attempts_left": result_data.get("attempts_left", 0),
                        "can_retry": result_data.get("attempts_left", 0) > 0
                    },
                    next_action=self._get_next_action_for_cpf_error(
                        result.error_code,
                        result_data.get("attempts_left", 0)
                    )
                )

        except Exception as e:
            logger.error(f"Erro ao processar CPF para usuário {user_id}: {e}", exc_info=True)
            return CPFVerificationResult(
                success=False,
                message="Erro interno do sistema. Tente novamente mais tarde.",
                error_code="system_error",
                next_action="retry_later"
            )

    async def cancel_verification(
        self,
        user_id: int,
        username: str,
        reason: str = "Cancelado pelo usuário"
    ) -> CPFVerificationResult:
        """
        Cancela uma verificação de CPF.

        Args:
            user_id: ID do usuário
            username: Nome de usuário
            reason: Motivo do cancelamento

        Returns:
            CPFVerificationResult: Resultado da operação
        """
        try:
            logger.info(f"Cancelando verificação para usuário {username} (ID: {user_id})")

            command = CancelCPFVerificationCommand(
                user_id=user_id,
                username=username,
                reason=reason
            )

            result = await self.cancel_handler.handle(command)

            if result.success:
                return CPFVerificationResult(
                    success=True,
                    verification_id=result.data.get("verification_id"),
                    message="Verificação cancelada com sucesso",
                    status="cancelled",
                    next_action="verification_cancelled"
                )
            else:
                return CPFVerificationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code,
                    next_action="contact_support"
                )

        except Exception as e:
            logger.error(f"Erro ao cancelar verificação para usuário {user_id}: {e}")
            return CPFVerificationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error",
                next_action="contact_support"
            )

    async def get_verification_status(self, user_id: int) -> CPFVerificationResult:
        """
        Obtém status atual da verificação do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            CPFVerificationResult: Status da verificação
        """
        try:
            # Repositório espera int, não UserId, e retorna lista
            verifications = await self.verification_repository.find_by_user_id(user_id)

            if not verifications:
                return CPFVerificationResult(
                    success=True,
                    message="Nenhuma verificação encontrada",
                    status="none",
                    next_action="start_verification"
                )

            # Pega a verificação mais recente
            verification = verifications[0]

            # Verifica se expirou
            if verification.is_expired() and verification.status == VerificationStatus.PENDING:
                return CPFVerificationResult(
                    success=True,
                    verification_id=str(verification.id),
                    message="Verificação expirou",
                    status="expired",
                    data={
                        "expired_at": verification.expires_at.isoformat(),
                        "verification_type": verification.verification_type.value
                    },
                    next_action="start_new_verification"
                )

            return CPFVerificationResult(
                success=True,
                verification_id=str(verification.id),
                message=f"Verificação está {verification.status.value}",
                status=verification.status.value,
                data={
                    "verification_type": verification.verification_type.value,
                    "created_at": verification.created_at.isoformat(),
                    "expires_at": verification.expires_at.isoformat(),
                    "attempt_count": verification.attempt_count,
                    "attempts_left": verification.has_attempts_left(),
                    "time_remaining": str(verification.get_time_remaining()),
                    "completed_at": verification.completed_at.isoformat() if verification.completed_at else None
                },
                next_action=self._get_next_action_for_status(verification.status)
            )

        except Exception as e:
            logger.error(f"Erro ao obter status de verificação para usuário {user_id}: {e}")
            return CPFVerificationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    async def process_expired_verifications(self) -> Dict[str, Any]:
        """
        Processa verificações expiradas (para uso em jobs/schedulers).

        Returns:
            Dict[str, Any]: Resultado do processamento
        """
        try:
            command = ProcessExpiredVerificationsCommand()
            result = await self.expire_handler.handle(command)

            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }

        except Exception as e:
            logger.error(f"Erro ao processar verificações expiradas: {e}")
            return {
                "success": False,
                "message": "Erro interno do sistema",
                "error": str(e)
            }

    def _validate_user_data(self, user_id: int, username: str) -> bool:
        """Valida dados básicos do usuário."""
        return (
            isinstance(user_id, int) and
            user_id > 0 and
            isinstance(username, str) and
            len(username.strip()) > 0
        )

    async def _check_rate_limiting(self, user_id: int) -> 'RateLimitResult':
        """Verifica rate limiting para o usuário."""
        try:
            # Repositório espera int, não UserId
            attempts_24h = await self.verification_repository.count_attempts_by_user(UserId(user_id), 24)

            max_attempts_24h = 5  # Máximo 5 tentativas por dia
            if attempts_24h >= max_attempts_24h:
                return RateLimitResult(
                    allowed=False,
                    message="Muitas tentativas de verificação nas últimas 24 horas",
                    retry_after=datetime.now() + timedelta(hours=24)
                )

            return RateLimitResult(allowed=True)

        except Exception as e:
            logger.error(f"Erro ao verificar rate limiting para usuário {user_id}: {e}")
            return RateLimitResult(allowed=True)  # Em caso de erro, permite a operação

    def _sanitize_cpf(self, cpf: str) -> str:
        """Sanitiza CPF removendo caracteres não numéricos."""
        return ''.join(filter(str.isdigit, cpf))

    async def _get_verification_context(self, user_id: int) -> Dict[str, Any]:
        """Obtém contexto atual da verificação."""
        try:
            # Repositório espera int, não UserId
            verifications = await self.verification_repository.find_by_user_id(user_id)

            if not verifications:
                return {"status": "none"}

            # Pega a verificação mais recente
            verification = verifications[0]

            return {
                "status": verification.status.value,
                "attempts": verification.attempt_count,
                "attempts_left": verification.has_attempts_left(),
                "expires_at": verification.expires_at.isoformat()
            }

        except Exception:
            return {"status": "unknown"}

    def _get_next_action_for_error(self, error_code: str) -> str:
        """Determina próxima ação baseada no código de erro."""
        action_map = {
            "user_not_found": "register_user",
            "verification_already_pending": "check_pending_verification",
            "invalid_verification_type": "fix_verification_type",
            "rate_limited": "wait_before_retry",
            "system_error": "retry_later"
        }
        return action_map.get(error_code, "contact_support")

    def _get_next_action_for_cpf_error(self, error_code: str, attempts_left: int) -> str:
        """Determina próxima ação baseada no erro de CPF."""
        if attempts_left > 0:
            if error_code == "invalid_cpf_format":
                return "provide_valid_cpf"
            elif error_code == "cpf_duplicate":
                return "resolve_duplicate"
            elif error_code == "cpf_not_found":
                return "check_cpf_registration"
            else:
                return "retry_cpf"
        else:
            return "contact_support"

    def _get_next_action_for_status(self, status: VerificationStatus) -> str:
        """Determina próxima ação baseada no status."""
        action_map = {
            VerificationStatus.PENDING: "provide_cpf",
            VerificationStatus.IN_PROGRESS: "wait_for_processing",
            VerificationStatus.COMPLETED: "verification_complete",
            VerificationStatus.FAILED: "start_new_verification",
            VerificationStatus.EXPIRED: "start_new_verification",
            VerificationStatus.CANCELLED: "start_new_verification"
        }
        return action_map.get(status, "contact_support")


@dataclass
class RateLimitResult:
    """Resultado de verificação de rate limiting."""
    allowed: bool
    message: str = ""
    retry_after: Optional[datetime] = None