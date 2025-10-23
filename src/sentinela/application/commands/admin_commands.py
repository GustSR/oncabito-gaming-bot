"""
Commands para operações administrativas.

Define comandos que podem ser executados por administradores
para gerenciar tickets, usuários e sistema.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from .base import Command


# ============================================================================
# USER ADMIN COMMANDS
# ============================================================================

@dataclass(frozen=True)
class ListUsersCommand(Command):
    """
    Comando para listar usuários.

    Attributes:
        admin_user_id: ID do administrador
        search_term: Termo de busca (nome/CPF mascarado)
        status_filter: Filtro por status
        verification_status: Filtro por status de verificação
        limit: Limite de resultados
        offset: Offset para paginação
    """
    admin_user_id: int
    search_term: Optional[str] = None
    status_filter: Optional[str] = None
    verification_status: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class BanUserCommand(Command):
    """
    Comando para banir um usuário.

    Attributes:
        admin_user_id: ID do administrador
        target_user_id: ID do usuário a ser banido
        reason: Motivo do banimento
        duration_hours: Duração do banimento em horas (None = permanente)
        revoke_access: Se deve revogar acessos imediatamente
    """
    admin_user_id: int
    target_user_id: int
    reason: str
    duration_hours: Optional[int] = None
    revoke_access: bool = True


@dataclass(frozen=True)
class UnbanUserCommand(Command):
    """
    Comando para desbanir um usuário.

    Attributes:
        admin_user_id: ID do administrador
        target_user_id: ID do usuário a ser desbanido
        reason: Motivo do desbloqueio
        restore_access: Se deve restaurar acessos
    """
    admin_user_id: int
    target_user_id: int
    reason: str
    restore_access: bool = True


@dataclass(frozen=True)
class ResetUserCPFCommand(Command):
    """
    Comando para resetar verificação de CPF de um usuário.

    Attributes:
        admin_user_id: ID do administrador
        target_user_id: ID do usuário
        reason: Motivo do reset
        force_reverification: Se deve forçar nova verificação
    """
    admin_user_id: int
    target_user_id: int
    reason: str
    force_reverification: bool = True


@dataclass(frozen=True)
class UpdateUserDataCommand(Command):
    """
    Comando para atualizar dados de um usuário.

    Attributes:
        admin_user_id: ID do administrador
        target_user_id: ID do usuário
        updates: Dicionário com campos a serem atualizados
        reason: Motivo da atualização
    """
    admin_user_id: int
    target_user_id: int
    updates: Dict[str, Any]
    reason: str


# ============================================================================
# VERIFICATION ADMIN COMMANDS
# ============================================================================

@dataclass(frozen=True)
class ListVerificationsCommand(Command):
    """
    Comando para listar verificações de CPF.

    Attributes:
        admin_user_id: ID do administrador
        status_filter: Filtro por status
        type_filter: Filtro por tipo
        date_from: Data inicial (opcional)
        date_to: Data final (opcional)
        limit: Limite de resultados
        offset: Offset para paginação
    """
    admin_user_id: int
    status_filter: Optional[str] = None
    type_filter: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ForceExpireVerificationCommand(Command):
    """
    Comando para forçar expiração de uma verificação.

    Attributes:
        admin_user_id: ID do administrador
        verification_id: ID da verificação
        reason: Motivo da expiração forçada
    """
    admin_user_id: int
    verification_id: str
    reason: str


@dataclass(frozen=True)
class ApproveVerificationCommand(Command):
    """
    Comando para aprovar manualmente uma verificação.

    Attributes:
        admin_user_id: ID do administrador
        verification_id: ID da verificação
        cpf: CPF aprovado
        client_data: Dados do cliente
        notes: Notas da aprovação
    """
    admin_user_id: int
    verification_id: str
    cpf: str
    client_data: Dict[str, Any]
    notes: str


@dataclass(frozen=True)
class ResolveCPFConflictCommand(Command):
    """
    Comando para resolver conflito de CPF duplicado.

    Attributes:
        admin_user_id: ID do administrador
        cpf: CPF em conflito
        primary_user_id: ID do usuário que ficará com o CPF
        secondary_user_id: ID do usuário que perderá o CPF
        resolution_action: Ação de resolução
        notes: Notas da resolução
    """
    admin_user_id: int
    cpf: str
    primary_user_id: int
    secondary_user_id: int
    resolution_action: str  # "keep_primary", "transfer_to_secondary", "manual_review"
    notes: str


# ============================================================================
# SYSTEM ADMIN COMMANDS
# ============================================================================

@dataclass(frozen=True)
class GetSystemStatsCommand(Command):
    """
    Comando para obter estatísticas do sistema.

    Attributes:
        admin_user_id: ID do administrador
        include_details: Se deve incluir detalhes granulares
        date_range_days: Período em dias para estatísticas
    """
    admin_user_id: int
    include_details: bool = False
    date_range_days: int = 30


@dataclass(frozen=True)
class RunMaintenanceCommand(Command):
    """
    Comando para executar manutenção do sistema.

    Attributes:
        admin_user_id: ID do administrador
        maintenance_type: Tipo de manutenção
        parameters: Parâmetros específicos da manutenção
        dry_run: Se é apenas simulação
    """
    admin_user_id: int
    maintenance_type: str  # "cleanup_old_data", "expire_verifications", "sync_hubsoft"
    parameters: Dict[str, Any]
    dry_run: bool = False


@dataclass(frozen=True)
class SendBroadcastMessageCommand(Command):
    """
    Comando para enviar mensagem broadcast.

    Attributes:
        admin_user_id: ID do administrador
        message: Mensagem a ser enviada
        target_group: Grupo alvo (all, verified_users, active_tickets)
        schedule_time: Horário para envio (None = imediato)
        priority: Prioridade da mensagem
    """
    admin_user_id: int
    message: str
    target_group: str = "all"
    schedule_time: Optional[datetime] = None
    priority: str = "normal"  # "low", "normal", "high", "urgent"


@dataclass(frozen=True)
class ExportDataCommand(Command):
    """
    Comando para exportar dados do sistema.

    Attributes:
        admin_user_id: ID do administrador
        export_type: Tipo de dados a exportar
        format: Formato do export (csv, xlsx, json)
        date_from: Data inicial
        date_to: Data final
        filters: Filtros específicos
    """
    admin_user_id: int
    export_type: str  # "tickets", "users", "verifications", "audit_logs"
    format: str = "csv"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ConfigureSystemSettingCommand(Command):
    """
    Comando para configurar definições do sistema.

    Attributes:
        admin_user_id: ID do administrador
        setting_key: Chave da configuração
        setting_value: Valor da configuração
        category: Categoria da configuração
        description: Descrição da mudança
    """
    admin_user_id: int
    setting_key: str
    setting_value: Any
    category: str
    description: str