"""
Base classes para Commands.

Define interfaces e classes base para o padrão Command
usado na camada de aplicação.
"""

from abc import ABC


class Command(ABC):
    """
    Classe base para todos os comandos.

    Commands são objetos que encapsulam uma solicitação
    de operação na camada de aplicação.

    Características:
    - Imutáveis (frozen dataclasses)
    - Contêm apenas dados
    - Não contêm lógica de negócio
    - São validados pelos handlers
    """
    pass