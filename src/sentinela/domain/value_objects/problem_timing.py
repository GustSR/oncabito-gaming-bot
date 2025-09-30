"""
Problem Timing Value Object.

Define quando o problema está ocorrendo.
"""

from dataclasses import dataclass
from enum import Enum


class TimingType(Enum):
    """Tipos de timing do problema."""
    NOW = "now"
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    INTERMITTENT = "intermittent"
    ALWAYS = "always"


@dataclass(frozen=True)
class ProblemTiming:
    """
    Value object para timing do problema.

    Attributes:
        timing_type: Tipo do timing
        display_name: Nome para exibição
    """
    timing_type: TimingType
    display_name: str

    def __post_init__(self):
        if not self.display_name.strip():
            raise ValueError("Display name não pode estar vazio")

    @classmethod
    def now(cls) -> 'ProblemTiming':
        """Problema ocorrendo agora."""
        return cls(TimingType.NOW, "🚨 Agora mesmo / Hoje")

    @classmethod
    def today(cls) -> 'ProblemTiming':
        """Problema começou hoje."""
        return cls(TimingType.TODAY, "📅 Hoje")

    @classmethod
    def yesterday(cls) -> 'ProblemTiming':
        """Problema começou ontem."""
        return cls(TimingType.YESTERDAY, "📅 Ontem")

    @classmethod
    def this_week(cls) -> 'ProblemTiming':
        """Problema começou esta semana."""
        return cls(TimingType.THIS_WEEK, "📅 Esta semana")

    @classmethod
    def intermittent(cls) -> 'ProblemTiming':
        """Problema intermitente."""
        return cls(TimingType.INTERMITTENT, "🔄 Intermitente")

    @classmethod
    def always(cls) -> 'ProblemTiming':
        """Problema sempre presente."""
        return cls(TimingType.ALWAYS, "⏰ Sempre")

    @classmethod
    def from_string(cls, timing_str: str) -> 'ProblemTiming':
        """Cria ProblemTiming a partir de string."""
        timing_str_lower = timing_str.lower().strip()

        mapping = {
            "agora": cls.now(),
            "agora mesmo": cls.now(),
            "hoje": cls.today(),
            "ontem": cls.yesterday(),
            "esta semana": cls.this_week(),
            "intermitente": cls.intermittent(),
            "sempre": cls.always(),
            "now": cls.now(),
            "today": cls.today(),
            "yesterday": cls.yesterday(),
            "this week": cls.this_week(),
            "intermittent": cls.intermittent(),
            "always": cls.always()
        }

        return mapping.get(timing_str_lower, cls.now())

    def is_urgent(self) -> bool:
        """Verifica se o timing indica urgência."""
        urgent_types = {TimingType.NOW, TimingType.TODAY, TimingType.ALWAYS}
        return self.timing_type in urgent_types

    def priority_score(self) -> int:
        """Retorna score de prioridade baseado no timing."""
        scores = {
            TimingType.NOW: 5,
            TimingType.TODAY: 4,
            TimingType.ALWAYS: 4,
            TimingType.YESTERDAY: 3,
            TimingType.INTERMITTENT: 2,
            TimingType.THIS_WEEK: 1
        }
        return scores.get(self.timing_type, 1)