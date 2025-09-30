"""
Base classes para Use Cases.

Define interfaces e classes base para use cases
na camada de aplicação.
"""

from abc import ABC
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class UseCaseResult:
    """
    Resultado da execução de um use case.

    Attributes:
        success: Se o use case foi executado com sucesso
        message: Mensagem descritiva do resultado
        data: Dados retornados pelo use case (opcional)
        error_code: Código de erro (se aplicável)
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

    @classmethod
    def success_result(cls, data: Optional[Dict[str, Any]] = None, message: str = "Operação realizada com sucesso") -> 'UseCaseResult':
        """
        Cria um resultado de sucesso.

        Args:
            data: Dados retornados
            message: Mensagem de sucesso

        Returns:
            UseCaseResult: Resultado de sucesso
        """
        return cls(success=True, message=message, data=data)

    @classmethod
    def failure_result(cls, error_code: str, message: str, data: Optional[Dict[str, Any]] = None) -> 'UseCaseResult':
        """
        Cria um resultado de falha.

        Args:
            error_code: Código do erro
            message: Mensagem de erro
            data: Dados adicionais do erro

        Returns:
            UseCaseResult: Resultado de falha
        """
        return cls(success=False, message=message, data=data, error_code=error_code)


class UseCase(ABC):
    """
    Classe base para todos os use cases.

    Use cases são responsáveis por orquestrar operações
    complexas na camada de aplicação, coordenando
    múltiplos command handlers e domain services.
    """
    pass