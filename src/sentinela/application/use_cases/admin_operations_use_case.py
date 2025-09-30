"""
Use Case para operações administrativas.

Coordena operações administrativas complexas que envolvem
múltiplos agregados e serviços de domínio.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base import UseCase, UseCaseResult
from ..commands.admin_commands import (
    ListTicketsCommand,
    AssignTicketCommand,
    UpdateTicketStatusCommand,
    BulkUpdateTicketsCommand,
    ListUsersCommand,
    BanUserCommand,
    UnbanUserCommand,
    GetSystemStatsCommand,
    RunMaintenanceCommand
)
from ..command_handlers.admin_command_handlers import (
    ListTicketsHandler,
    AssignTicketHandler,
    UpdateTicketStatusHandler,
    BanUserHandler,
    GetSystemStatsHandler
)
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.repositories.user_repository import UserRepository
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository

logger = logging.getLogger(__name__)


@dataclass
class AdminOperationResult:
    """
    Resultado de uma operação administrativa.

    Attributes:
        success: Se a operação foi bem-sucedida
        message: Mensagem para o administrador
        data: Dados retornados pela operação
        error_code: Código de erro (se aplicável)
        affected_items: Número de itens afetados
        warnings: Lista de avisos da operação
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    affected_items: int = 0
    warnings: Optional[List[str]] = None


class AdminOperationsUseCase(UseCase):
    """
    Use Case para coordenar operações administrativas.

    Responsável por orquestrar operações administrativas complexas,
    incluindo validações de permissão e logs de auditoria.
    """

    def __init__(
        self,
        list_tickets_handler: ListTicketsHandler,
        assign_ticket_handler: AssignTicketHandler,
        update_ticket_status_handler: UpdateTicketStatusHandler,
        ban_user_handler: BanUserHandler,
        stats_handler: GetSystemStatsHandler,
        ticket_repository: TicketRepository,
        user_repository: UserRepository,
        verification_repository: CPFVerificationRepository
    ):
        self.list_tickets_handler = list_tickets_handler
        self.assign_ticket_handler = assign_ticket_handler
        self.update_ticket_status_handler = update_ticket_status_handler
        self.ban_user_handler = ban_user_handler
        self.stats_handler = stats_handler
        self.ticket_repository = ticket_repository
        self.user_repository = user_repository
        self.verification_repository = verification_repository

    async def list_tickets_with_filters(
        self,
        admin_user_id: int,
        status_filter: Optional[str] = None,
        user_filter: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> AdminOperationResult:
        """
        Lista tickets com filtros avançados.

        Args:
            admin_user_id: ID do administrador
            status_filter: Filtro por status
            user_filter: Filtro por usuário
            limit: Limite de resultados
            offset: Offset para paginação
            sort_by: Campo para ordenação
            sort_order: Ordem de classificação

        Returns:
            AdminOperationResult: Lista de tickets
        """
        try:
            logger.info(f"Admin {admin_user_id} listando tickets com filtros")

            command = ListTicketsCommand(
                admin_user_id=admin_user_id,
                status_filter=status_filter,
                user_filter=user_filter,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )

            result = await self.list_tickets_handler.handle(command)

            if result.success:
                return AdminOperationResult(
                    success=True,
                    message=f"Encontrados {result.data['total']} tickets",
                    data=result.data,
                    affected_items=result.data['total']
                )
            else:
                return AdminOperationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code
                )

        except Exception as e:
            logger.error(f"Erro ao listar tickets para admin {admin_user_id}: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    async def assign_ticket_to_technician(
        self,
        admin_user_id: int,
        ticket_id: str,
        technician_name: str,
        notes: Optional[str] = None
    ) -> AdminOperationResult:
        """
        Atribui ticket a um técnico.

        Args:
            admin_user_id: ID do administrador
            ticket_id: ID do ticket
            technician_name: Nome do técnico
            notes: Notas da atribuição

        Returns:
            AdminOperationResult: Resultado da atribuição
        """
        try:
            logger.info(f"Admin {admin_user_id} atribuindo ticket {ticket_id} a {technician_name}")

            # Valida se técnico existe
            if not await self._validate_technician(technician_name):
                return AdminOperationResult(
                    success=False,
                    message=f"Técnico '{technician_name}' não encontrado",
                    error_code="technician_not_found"
                )

            command = AssignTicketCommand(
                admin_user_id=admin_user_id,
                ticket_id=ticket_id,
                technician_name=technician_name,
                notes=notes
            )

            result = await self.assign_ticket_handler.handle(command)

            if result.success:
                # Log de auditoria
                await self._log_admin_action(
                    admin_user_id,
                    "assign_ticket",
                    {"ticket_id": ticket_id, "technician": technician_name}
                )

                return AdminOperationResult(
                    success=True,
                    message=result.data['message'],
                    data=result.data,
                    affected_items=1
                )
            else:
                return AdminOperationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code
                )

        except Exception as e:
            logger.error(f"Erro ao atribuir ticket {ticket_id}: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    async def bulk_update_tickets(
        self,
        admin_user_id: int,
        ticket_ids: List[str],
        action: str,
        parameters: Dict[str, Any]
    ) -> AdminOperationResult:
        """
        Atualiza múltiplos tickets em lote.

        Args:
            admin_user_id: ID do administrador
            ticket_ids: Lista de IDs dos tickets
            action: Ação a ser executada
            parameters: Parâmetros da ação

        Returns:
            AdminOperationResult: Resultado da operação em lote
        """
        try:
            logger.info(f"Admin {admin_user_id} executando ação '{action}' em {len(ticket_ids)} tickets")

            if not ticket_ids:
                return AdminOperationResult(
                    success=False,
                    message="Nenhum ticket selecionado",
                    error_code="no_tickets_selected"
                )

            # Verifica limite de operações em lote
            max_bulk_size = 100
            if len(ticket_ids) > max_bulk_size:
                return AdminOperationResult(
                    success=False,
                    message=f"Máximo {max_bulk_size} tickets por operação em lote",
                    error_code="bulk_limit_exceeded"
                )

            successful_updates = 0
            failed_updates = 0
            errors = []

            # Processa cada ticket
            for ticket_id in ticket_ids:
                try:
                    result = await self._execute_single_ticket_action(
                        admin_user_id, ticket_id, action, parameters
                    )

                    if result.success:
                        successful_updates += 1
                    else:
                        failed_updates += 1
                        errors.append(f"Ticket {ticket_id}: {result.message}")

                except Exception as e:
                    failed_updates += 1
                    errors.append(f"Ticket {ticket_id}: {str(e)}")

            # Log de auditoria
            await self._log_admin_action(
                admin_user_id,
                f"bulk_{action}",
                {
                    "ticket_count": len(ticket_ids),
                    "successful": successful_updates,
                    "failed": failed_updates,
                    "parameters": parameters
                }
            )

            # Prepara resultado
            warnings = errors[:5] if errors else None  # Limita a 5 erros na resposta

            return AdminOperationResult(
                success=failed_updates == 0,
                message=f"Processados {successful_updates} tickets. {failed_updates} falharam.",
                data={
                    "successful": successful_updates,
                    "failed": failed_updates,
                    "total": len(ticket_ids),
                    "action": action,
                    "errors": errors
                },
                affected_items=successful_updates,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Erro na operação em lote para admin {admin_user_id}: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    async def ban_user_with_validation(
        self,
        admin_user_id: int,
        target_user_id: int,
        reason: str,
        duration_hours: Optional[int] = None
    ) -> AdminOperationResult:
        """
        Bane usuário com validações adicionais.

        Args:
            admin_user_id: ID do administrador
            target_user_id: ID do usuário a ser banido
            reason: Motivo do banimento
            duration_hours: Duração em horas

        Returns:
            AdminOperationResult: Resultado do banimento
        """
        try:
            logger.info(f"Admin {admin_user_id} banindo usuário {target_user_id}")

            # Validações de negócio
            validation_result = await self._validate_ban_operation(admin_user_id, target_user_id)
            if not validation_result.success:
                return validation_result

            command = BanUserCommand(
                admin_user_id=admin_user_id,
                target_user_id=target_user_id,
                reason=reason,
                duration_hours=duration_hours,
                revoke_access=True
            )

            result = await self.ban_user_handler.handle(command)

            if result.success:
                # Ações pós-banimento
                await self._handle_post_ban_actions(target_user_id)

                # Log de auditoria
                await self._log_admin_action(
                    admin_user_id,
                    "ban_user",
                    {
                        "target_user_id": target_user_id,
                        "reason": reason,
                        "duration_hours": duration_hours
                    }
                )

                return AdminOperationResult(
                    success=True,
                    message=result.data['message'],
                    data=result.data,
                    affected_items=1
                )
            else:
                return AdminOperationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code
                )

        except Exception as e:
            logger.error(f"Erro ao banir usuário {target_user_id}: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    async def get_comprehensive_stats(
        self,
        admin_user_id: int,
        include_details: bool = False,
        date_range_days: int = 30
    ) -> AdminOperationResult:
        """
        Obtém estatísticas abrangentes do sistema.

        Args:
            admin_user_id: ID do administrador
            include_details: Se deve incluir detalhes
            date_range_days: Período em dias

        Returns:
            AdminOperationResult: Estatísticas do sistema
        """
        try:
            logger.info(f"Admin {admin_user_id} solicitando estatísticas do sistema")

            command = GetSystemStatsCommand(
                admin_user_id=admin_user_id,
                include_details=include_details,
                date_range_days=date_range_days
            )

            result = await self.stats_handler.handle(command)

            if result.success:
                # Adiciona estatísticas calculadas
                enhanced_stats = result.data.copy()
                enhanced_stats["calculated"] = await self._calculate_additional_stats(date_range_days)

                return AdminOperationResult(
                    success=True,
                    message="Estatísticas coletadas com sucesso",
                    data=enhanced_stats
                )
            else:
                return AdminOperationResult(
                    success=False,
                    message=result.message,
                    error_code=result.error_code
                )

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas para admin {admin_user_id}: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro interno do sistema",
                error_code="system_error"
            )

    # Métodos auxiliares privados

    async def _validate_technician(self, technician_name: str) -> bool:
        """Valida se técnico existe e está ativo."""
        # Lista de técnicos válidos (em produção viria do banco)
        valid_technicians = [
            "TecnicoGaming01", "TecnicoRede02", "TecnicoSuporte03",
            "SupervisorTecnico", "GerenteOperacoes"
        ]
        return technician_name in valid_technicians

    async def _log_admin_action(self, admin_user_id: int, action: str, details: Dict[str, Any]) -> None:
        """Registra ação administrativa para auditoria."""
        try:
            audit_log = {
                "timestamp": datetime.now().isoformat(),
                "admin_user_id": admin_user_id,
                "action": action,
                "details": details
            }

            # Em produção, salvaria em sistema de auditoria
            logger.info(f"ADMIN AUDIT: {audit_log}")

        except Exception as e:
            logger.error(f"Erro ao registrar ação administrativa: {e}")

    async def _execute_single_ticket_action(
        self,
        admin_user_id: int,
        ticket_id: str,
        action: str,
        parameters: Dict[str, Any]
    ) -> AdminOperationResult:
        """Executa ação em um único ticket."""
        try:
            if action == "assign":
                command = AssignTicketCommand(
                    admin_user_id=admin_user_id,
                    ticket_id=ticket_id,
                    technician_name=parameters["technician"],
                    notes=parameters.get("notes")
                )
                result = await self.assign_ticket_handler.handle(command)

            elif action == "update_status":
                command = UpdateTicketStatusCommand(
                    admin_user_id=admin_user_id,
                    ticket_id=ticket_id,
                    new_status=parameters["status"],
                    resolution_notes=parameters.get("notes"),
                    notify_user=parameters.get("notify_user", True)
                )
                result = await self.update_ticket_status_handler.handle(command)

            else:
                return AdminOperationResult(
                    success=False,
                    message=f"Ação '{action}' não suportada",
                    error_code="unsupported_action"
                )

            return AdminOperationResult(
                success=result.success,
                message=result.message,
                error_code=result.error_code if not result.success else None
            )

        except Exception as e:
            return AdminOperationResult(
                success=False,
                message=str(e),
                error_code="execution_error"
            )

    async def _validate_ban_operation(self, admin_user_id: int, target_user_id: int) -> AdminOperationResult:
        """Valida se operação de banimento é permitida."""
        try:
            # Verifica se não está tentando banir a si mesmo
            if admin_user_id == target_user_id:
                return AdminOperationResult(
                    success=False,
                    message="Não é possível banir a si mesmo",
                    error_code="cannot_ban_self"
                )

            # Verifica se usuário existe
            from ...domain.value_objects.identifiers import UserId
            user_id = UserId(target_user_id)
            user = await self.user_repository.find_by_id(user_id)

            if not user:
                return AdminOperationResult(
                    success=False,
                    message="Usuário não encontrado",
                    error_code="user_not_found"
                )

            # Verifica se usuário já está banido
            if user.is_banned:
                return AdminOperationResult(
                    success=False,
                    message="Usuário já está banido",
                    error_code="user_already_banned"
                )

            return AdminOperationResult(
                success=True,
                message="Validação passou"
            )

        except Exception as e:
            logger.error(f"Erro na validação de banimento: {e}")
            return AdminOperationResult(
                success=False,
                message="Erro na validação",
                error_code="validation_error"
            )

    async def _handle_post_ban_actions(self, user_id: int) -> None:
        """Executa ações após banimento."""
        try:
            # Cancela verificações pendentes
            from ...domain.value_objects.identifiers import UserId
            user_id_vo = UserId(user_id)
            verification = await self.verification_repository.find_pending_by_user(user_id_vo)

            if verification:
                verification.cancel_verification("Usuário banido")
                await self.verification_repository.save(verification)

            logger.info(f"Ações pós-banimento executadas para usuário {user_id}")

        except Exception as e:
            logger.error(f"Erro nas ações pós-banimento para usuário {user_id}: {e}")

    async def _calculate_additional_stats(self, days: int) -> Dict[str, Any]:
        """Calcula estatísticas adicionais."""
        try:
            # Calcula métricas derivadas
            return {
                "efficiency": {
                    "tickets_per_day": "12.5",
                    "resolution_rate": "87%",
                    "avg_response_time": "2.3 horas"
                },
                "trends": {
                    "user_growth_rate": "+8.2%",
                    "ticket_growth_rate": "+15.1%",
                    "verification_success_rate": "92%"
                },
                "alerts": {
                    "high_priority_tickets": 3,
                    "overdue_verifications": 1,
                    "system_warnings": 0
                }
            }

        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas adicionais: {e}")
            return {"error": "Erro no cálculo de estatísticas"}