import logging
from enum import Enum
from functools import wraps
from typing import List, Set, Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AccessLevel(Enum):
    """Níveis de acesso no sistema"""
    USER = "user"           # Usuários comuns (verificados)
    ADMIN = "admin"         # Administradores do sistema
    SUPER_ADMIN = "super_admin"  # Super administradores (futuro)

class PermissionManager:
    """Gerenciador de permissões e controle de acesso"""

    # Definição dos comandos por nível de acesso
    COMMAND_PERMISSIONS = {
        AccessLevel.USER: {
            "start", "status", "suporte", "help"
        },
        AccessLevel.ADMIN: {
            # Inclui todos os comandos de usuário comum
            "start", "status", "suporte", "help",
            # Comandos administrativos
            "admin_tickets", "sync_tickets", "health_hubsoft",
            "test_group", "topics", "auto_config", "test_topics", "scan_topics",
            # Comandos de gerenciamento de administradores
            "sync_admins", "list_admins"
        }
    }

    @classmethod
    def get_user_access_level(cls, user_id: int) -> AccessLevel:
        """
        Determina o nível de acesso de um usuário.
        Prioriza administradores detectados automaticamente, com fallback para configuração manual.

        Args:
            user_id: ID do usuário no Telegram

        Returns:
            AccessLevel: Nível de acesso do usuário
        """
        try:
            # 1. Primeiro verifica se é administrador detectado automaticamente
            from src.sentinela.clients.db_client import is_stored_administrator
            if is_stored_administrator(user_id):
                return AccessLevel.ADMIN

            # 2. Fallback para configuração manual (para compatibilidade)
            from src.sentinela.core.config import ADMIN_USER_IDS
            if ADMIN_USER_IDS and user_id in ADMIN_USER_IDS:
                return AccessLevel.ADMIN

            # 3. Verificar se é usuário verificado (tem dados no sistema)
            from src.sentinela.clients.db_client import get_user_data
            user_data = get_user_data(user_id)

            if user_data and user_data.get('cpf'):
                return AccessLevel.USER
            else:
                # Usuário não verificado - apenas acesso básico
                return AccessLevel.USER

        except Exception as e:
            logger.error(f"Erro ao determinar nível de acesso para usuário {user_id}: {e}")
            return AccessLevel.USER

    @classmethod
    def has_permission(cls, user_id: int, command: str) -> bool:
        """
        Verifica se um usuário tem permissão para executar um comando.

        Args:
            user_id: ID do usuário
            command: Nome do comando (sem /)

        Returns:
            bool: True se tem permissão, False caso contrário
        """
        try:
            user_level = cls.get_user_access_level(user_id)
            allowed_commands = cls.COMMAND_PERMISSIONS.get(user_level, set())

            return command in allowed_commands

        except Exception as e:
            logger.error(f"Erro ao verificar permissão do comando {command} para usuário {user_id}: {e}")
            return False

    @classmethod
    def get_available_commands(cls, user_id: int) -> Set[str]:
        """
        Retorna lista de comandos disponíveis para um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Set[str]: Conjunto de comandos disponíveis
        """
        try:
            user_level = cls.get_user_access_level(user_id)
            return cls.COMMAND_PERMISSIONS.get(user_level, set())
        except Exception as e:
            logger.error(f"Erro ao obter comandos disponíveis para usuário {user_id}: {e}")
            return {"start"}  # Fallback mínimo

    @classmethod
    def get_access_level_display(cls, level: AccessLevel) -> str:
        """Retorna texto amigável para o nível de acesso"""
        display_names = {
            AccessLevel.USER: "👤 Usuário",
            AccessLevel.ADMIN: "👑 Administrador",
            AccessLevel.SUPER_ADMIN: "⭐ Super Administrador"
        }
        return display_names.get(level, "❓ Desconhecido")

def require_access(level: AccessLevel):
    """
    Decorator para exigir nível mínimo de acesso em comandos.

    Args:
        level: Nível mínimo de acesso necessário

    Usage:
        @require_access(AccessLevel.ADMIN)
        async def admin_command(update, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            user_id = user.id
            username = user.username or user.first_name

            # Obtém nível do usuário
            user_level = PermissionManager.get_user_access_level(user_id)

            # Verifica se tem acesso suficiente
            required_levels = {
                AccessLevel.USER: [AccessLevel.USER, AccessLevel.ADMIN, AccessLevel.SUPER_ADMIN],
                AccessLevel.ADMIN: [AccessLevel.ADMIN, AccessLevel.SUPER_ADMIN],
                AccessLevel.SUPER_ADMIN: [AccessLevel.SUPER_ADMIN]
            }

            if user_level not in required_levels.get(level, []):
                await send_access_denied_message(update, user_level, level)
                logger.warning(f"Acesso negado: {username} (ID: {user_id}, Nível: {user_level.value}) tentou acessar comando que requer {level.value}")
                return

            # Log de acesso autorizado para comandos administrativos
            if level == AccessLevel.ADMIN:
                logger.info(f"Acesso autorizado: {username} (ID: {user_id}, Nível: {user_level.value}) executando comando administrativo")

            # Executa o comando original
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator

def require_command_permission(command_name: str):
    """
    Decorator específico para verificar permissão de comando.

    Args:
        command_name: Nome do comando (sem /)

    Usage:
        @require_command_permission("admin_tickets")
        async def admin_tickets_command(update, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            user_id = user.id
            username = user.username or user.first_name

            # Verifica permissão específica do comando
            if not PermissionManager.has_permission(user_id, command_name):
                user_level = PermissionManager.get_user_access_level(user_id)
                await send_command_not_available_message(update, command_name, user_level)
                logger.warning(f"Comando não autorizado: {username} (ID: {user_id}) tentou usar /{command_name}")
                return

            # Executa o comando original
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator

async def send_access_denied_message(update: Update, user_level: AccessLevel, required_level: AccessLevel):
    """Envia mensagem de acesso negado"""
    try:
        user_display = PermissionManager.get_access_level_display(user_level)
        required_display = PermissionManager.get_access_level_display(required_level)

        message = (
            f"🚫 <b>Acesso Negado</b>\n\n"
            f"👤 <b>Seu nível:</b> {user_display}\n"
            f"🔒 <b>Nível necessário:</b> {required_display}\n\n"
            f"💡 Este comando é restrito a usuários com permissões adequadas.\n\n"
            f"📞 Se você acredita que deveria ter acesso, contate um administrador."
        )

        await update.message.reply_html(message)

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de acesso negado: {e}")

async def send_command_not_available_message(update: Update, command_name: str, user_level: AccessLevel):
    """Envia mensagem quando comando não está disponível para o usuário"""
    try:
        user_display = PermissionManager.get_access_level_display(user_level)

        message = (
            f"❌ <b>Comando não disponível</b>\n\n"
            f"🔧 O comando <code>/{command_name}</code> não está disponível para seu nível de acesso.\n\n"
            f"👤 <b>Seu nível:</b> {user_display}\n\n"
            f"💡 <b>Comandos disponíveis para você:</b>\n"
        )

        # Lista comandos disponíveis
        available_commands = PermissionManager.get_available_commands(update.effective_user.id)
        for cmd in sorted(available_commands):
            message += f"• /{cmd}\n"

        message += f"\n📱 Use /help para ver detalhes dos comandos disponíveis."

        await update.message.reply_html(message)

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de comando não disponível: {e}")

def is_admin(user_id: int) -> bool:
    """
    Função auxiliar para verificar se usuário é admin.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se é admin, False caso contrário
    """
    return PermissionManager.get_user_access_level(user_id) == AccessLevel.ADMIN

def is_verified_user(user_id: int) -> bool:
    """
    Função auxiliar para verificar se usuário está verificado.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se está verificado, False caso contrário
    """
    try:
        from src.sentinela.clients.db_client import get_user_data
        user_data = get_user_data(user_id)
        return user_data is not None and user_data.get('cpf') is not None
    except:
        return False