"""
Game Title Value Object.

Define tipos de jogos suportados pelo sistema de suporte.
"""

from dataclasses import dataclass
from enum import Enum


class GameType(Enum):
    """Tipos de jogos suportados."""
    VALORANT = "valorant"
    CS2 = "cs2"
    FORTNITE = "fortnite"
    APEX_LEGENDS = "apex_legends"
    LOL = "lol"
    OVERWATCH = "overwatch"
    ROCKET_LEAGUE = "rocket_league"
    OTHER = "other"


@dataclass(frozen=True)
class GameTitle:
    """
    Value object para título do jogo.

    Attributes:
        game_type: Tipo do jogo
        display_name: Nome para exibição
    """
    game_type: GameType
    display_name: str

    def __post_init__(self):
        if not self.display_name.strip():
            raise ValueError("Display name não pode estar vazio")

    @classmethod
    def valorant(cls) -> 'GameTitle':
        """Cria GameTitle para Valorant."""
        return cls(GameType.VALORANT, "⚡️ Valorant")

    @classmethod
    def cs2(cls) -> 'GameTitle':
        """Cria GameTitle para CS2."""
        return cls(GameType.CS2, "🎯 Counter-Strike 2")

    @classmethod
    def fortnite(cls) -> 'GameTitle':
        """Cria GameTitle para Fortnite."""
        return cls(GameType.FORTNITE, "🏗️ Fortnite")

    @classmethod
    def apex_legends(cls) -> 'GameTitle':
        """Cria GameTitle para Apex Legends."""
        return cls(GameType.APEX_LEGENDS, "🦅 Apex Legends")

    @classmethod
    def lol(cls) -> 'GameTitle':
        """Cria GameTitle para League of Legends."""
        return cls(GameType.LOL, "⚔️ League of Legends")

    @classmethod
    def overwatch(cls) -> 'GameTitle':
        """Cria GameTitle para Overwatch."""
        return cls(GameType.OVERWATCH, "🤖 Overwatch 2")

    @classmethod
    def rocket_league(cls) -> 'GameTitle':
        """Cria GameTitle para Rocket League."""
        return cls(GameType.ROCKET_LEAGUE, "🚗 Rocket League")

    @classmethod
    def other(cls, display_name: str = "🎮 Outros") -> 'GameTitle':
        """Cria GameTitle para outros jogos."""
        return cls(GameType.OTHER, display_name)

    @classmethod
    def from_string(cls, game_str: str) -> 'GameTitle':
        """Cria GameTitle a partir de string."""
        game_str_lower = game_str.lower().strip()

        mapping = {
            "valorant": cls.valorant(),
            "cs2": cls.cs2(),
            "counter-strike": cls.cs2(),
            "counter strike": cls.cs2(),
            "fortnite": cls.fortnite(),
            "apex": cls.apex_legends(),
            "apex legends": cls.apex_legends(),
            "lol": cls.lol(),
            "league of legends": cls.lol(),
            "overwatch": cls.overwatch(),
            "rocket league": cls.rocket_league(),
        }

        return mapping.get(game_str_lower, cls.other(f"🎮 {game_str}"))