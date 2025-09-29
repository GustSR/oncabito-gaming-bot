"""
Base classes para Application Layer.

Define interfaces e classes base para Commands, Queries e Handlers.
"""

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class Command(ABC):
    """
    Base class para Commands.

    Commands representam intenções de modificar o estado do sistema.
    São imutáveis (frozen=True) e contêm apenas dados.

    Exemplos:
        - CreateUserCommand
        - VerifyUserCommand
        - UpdateUserCommand
    """
    pass


@dataclass(frozen=True)
class Query(ABC):
    """
    Base class para Queries.

    Queries representam intenções de consultar dados sem modificar estado.
    São imutáveis (frozen=True) e contêm apenas critérios de busca.

    Exemplos:
        - GetUserQuery
        - FindActiveUsersQuery
        - GetUserStatisticsQuery
    """
    pass


class CommandHandler(ABC):
    """
    Base class para Command Handlers.

    Command Handlers implementam a lógica de negócio para processar Commands.
    Cada handler é responsável por um único tipo de Command.

    Convenção:
        - Método handle(command: SpecificCommand) -> Result
        - Pode modificar estado via repositories
        - Pode disparar domain events
    """
    pass


class QueryHandler(ABC):
    """
    Base class para Query Handlers.

    Query Handlers implementam a lógica de consulta para processar Queries.
    Cada handler é responsável por um único tipo de Query.

    Convenção:
        - Método handle(query: SpecificQuery) -> Result
        - Apenas leitura (não modifica estado)
        - Pode usar read models otimizados
    """
    pass


class UseCase(ABC):
    """
    Base class para Use Cases complexos.

    Use Cases representam funcionalidades completas que podem
    envolver múltiplos Commands e Queries coordenados.

    Exemplos:
        - CompleteUserRegistrationUseCase
        - ProcessSupportTicketUseCase
        - GenerateReportUseCase
    """
    pass