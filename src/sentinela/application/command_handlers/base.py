"""
Base classes para Command Handlers.

Define interfaces e classes base para handlers de comandos
na camada de aplicação.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Dict, Any, Optional
from dataclasses import dataclass

from ..commands.base import Command

C = TypeVar('C', bound=Command)


@dataclass
class CommandResult:
    """
    Resultado da execução de um comando.

    Attributes:
        success: Se o comando foi executado com sucesso
        message: Mensagem descritiva do resultado
        data: Dados retornados pelo comando (opcional)
        error_code: Código de erro (se aplicável)
    """
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

    @classmethod
    def success(cls, message: str = "Operação realizada com sucesso", data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """
        Cria um resultado de sucesso.

        Args:
            data: Dados retornados
            message: Mensagem de sucesso

        Returns:
            CommandResult: Resultado de sucesso
        """
        return cls(success=True, message=message, data=data)

    @classmethod
    def failure(cls, error_code: str, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """
        Cria um resultado de falha.

        Args:
            error_code: Código do erro
            message: Mensagem de erro
            data: Dados adicionais do erro

        Returns:
            CommandResult: Resultado de falha
        """
        return cls(success=False, message=message, data=data, error_code=error_code)


class CommandHandler(Generic[C], ABC):
    """
    Interface base para handlers de comandos.

    Implementa o padrão Command Handler para processar comandos
    e executar operações na camada de aplicação.
    """

    @abstractmethod
    async def handle(self, command: C) -> CommandResult:
        """
        Processa um comando.

        Args:
            command: Comando a ser processado

        Returns:
            CommandResult: Resultado da execução
        """
        pass