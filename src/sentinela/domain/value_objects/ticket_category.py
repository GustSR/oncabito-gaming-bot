"""
Value Objects para categorias e tipos de tickets de suporte.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from .base import ValueObject, ValidationError


class TicketCategoryType(Enum):
    """Tipos de categoria de ticket de suporte."""
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    EQUIPMENT = "equipment"
    OTHER = "other"


class GameType(Enum):
    """Jogos populares para suporte."""
    VALORANT = "valorant"
    CS2 = "cs2"
    LOL = "lol"
    FORTNITE = "fortnite"
    APEX = "apex"
    OVERWATCH = "overwatch"
    MOBILE_LEGENDS = "mobile_legends"
    DOTA2 = "dota2"
    ALL_GAMES = "all_games"
    OTHER_GAME = "other_game"


class TimingType(Enum):
    """Quando o problema começou."""
    NOW = "now"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    LONG_TIME = "long_time"
    ALWAYS = "always"


@dataclass(frozen=True)
class TicketCategory(ValueObject):
    """
    Categoria do ticket de suporte.

    Attributes:
        category_type: Tipo da categoria
        display_name: Nome para exibição
    """
    category_type: TicketCategoryType
    display_name: str

    @classmethod
    def from_string(cls, category_str: str) -> 'TicketCategory':
        """
        Cria categoria a partir de string.

        Args:
            category_str: String da categoria

        Returns:
            TicketCategory: Categoria validada

        Raises:
            ValidationError: Se categoria inválida
        """
        category_mapping = {
            "connectivity": (TicketCategoryType.CONNECTIVITY, "🌐 Conectividade/Ping"),
            "performance": (TicketCategoryType.PERFORMANCE, "🎮 Performance em Jogos"),
            "configuration": (TicketCategoryType.CONFIGURATION, "⚙️ Configuração/Otimização"),
            "equipment": (TicketCategoryType.EQUIPMENT, "🔧 Problema com Equipamento"),
            "other": (TicketCategoryType.OTHER, "📞 Outro")
        }

        if category_str not in category_mapping:
            raise ValidationError(f"Categoria inválida: {category_str}")

        category_type, display_name = category_mapping[category_str]
        return cls(category_type, display_name)

    @classmethod
    def get_all_categories(cls) -> Dict[str, 'TicketCategory']:
        """Retorna todas as categorias disponíveis."""
        return {
            "connectivity": cls.from_string("connectivity"),
            "performance": cls.from_string("performance"),
            "configuration": cls.from_string("configuration"),
            "equipment": cls.from_string("equipment"),
            "other": cls.from_string("other")
        }


@dataclass(frozen=True)
class GameTitle(ValueObject):
    """
    Jogo afetado pelo problema.

    Attributes:
        game_type: Tipo do jogo
        display_name: Nome para exibição
        custom_name: Nome customizado (para "outro jogo")
    """
    game_type: GameType
    display_name: str
    custom_name: str = ""

    @classmethod
    def from_string(cls, game_str: str, custom_name: str = "") -> 'GameTitle':
        """
        Cria GameTitle a partir de string.

        Args:
            game_str: String do jogo
            custom_name: Nome customizado para "outro jogo"

        Returns:
            GameTitle: Jogo validado
        """
        game_mapping = {
            "valorant": (GameType.VALORANT, "⚡️ Valorant"),
            "cs2": (GameType.CS2, "🎯 CS2"),
            "lol": (GameType.LOL, "🏆 League of Legends"),
            "fortnite": (GameType.FORTNITE, "🌍 Fortnite"),
            "apex": (GameType.APEX, "🎮 Apex Legends"),
            "overwatch": (GameType.OVERWATCH, "🦸 Overwatch 2"),
            "mobile_legends": (GameType.MOBILE_LEGENDS, "📱 Mobile Legends"),
            "dota2": (GameType.DOTA2, "⚔️ Dota 2"),
            "all_games": (GameType.ALL_GAMES, "🌐 Todos os jogos"),
            "other_game": (GameType.OTHER_GAME, "📝 Outro jogo")
        }

        if game_str not in game_mapping:
            raise ValidationError(f"Jogo inválido: {game_str}")

        game_type, display_name = game_mapping[game_str]

        if game_type == GameType.OTHER_GAME and custom_name:
            display_name = f"📝 {custom_name}"

        return cls(game_type, display_name, custom_name)

    @classmethod
    def get_popular_games(cls) -> Dict[str, 'GameTitle']:
        """Retorna jogos populares disponíveis."""
        games = {}
        game_mapping = {
            "valorant": "⚡️ Valorant",
            "cs2": "🎯 CS2",
            "lol": "🏆 League of Legends",
            "fortnite": "🌍 Fortnite",
            "apex": "🎮 Apex Legends",
            "overwatch": "🦸 Overwatch 2",
            "mobile_legends": "📱 Mobile Legends",
            "dota2": "⚔️ Dota 2",
            "all_games": "🌐 Todos os jogos",
            "other_game": "📝 Outro jogo"
        }

        for key in game_mapping:
            games[key] = cls.from_string(key)

        return games


@dataclass(frozen=True)
class ProblemTiming(ValueObject):
    """
    Quando o problema começou.

    Attributes:
        timing_type: Tipo do timing
        display_name: Nome para exibição
    """
    timing_type: TimingType
    display_name: str

    @classmethod
    def from_string(cls, timing_str: str) -> 'ProblemTiming':
        """
        Cria ProblemTiming a partir de string.

        Args:
            timing_str: String do timing

        Returns:
            ProblemTiming: Timing validado
        """
        timing_mapping = {
            "now": (TimingType.NOW, "🚨 Agora mesmo / Hoje"),
            "yesterday": (TimingType.YESTERDAY, "📅 Ontem"),
            "this_week": (TimingType.THIS_WEEK, "📆 Esta semana"),
            "last_week": (TimingType.LAST_WEEK, "🗓️ Semana passada"),
            "long_time": (TimingType.LONG_TIME, "⏳ Há mais tempo"),
            "always": (TimingType.ALWAYS, "🔄 Sempre foi assim")
        }

        if timing_str not in timing_mapping:
            raise ValidationError(f"Timing inválido: {timing_str}")

        timing_type, display_name = timing_mapping[timing_str]
        return cls(timing_type, display_name)

    @classmethod
    def get_all_timings(cls) -> Dict[str, 'ProblemTiming']:
        """Retorna todas as opções de timing disponíveis."""
        timings = {}
        timing_mapping = {
            "now": "🚨 Agora mesmo / Hoje",
            "yesterday": "📅 Ontem",
            "this_week": "📆 Esta semana",
            "last_week": "🗓️ Semana passada",
            "long_time": "⏳ Há mais tempo",
            "always": "🔄 Sempre foi assim"
        }

        for key in timing_mapping:
            timings[key] = cls.from_string(key)

        return timings