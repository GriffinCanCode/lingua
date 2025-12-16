"""Abstract base class for language modules."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CaseConfig:
    """Configuration for a grammatical case."""
    id: str
    label: str
    hint: str
    color_bg: str
    color_text: str
    color_border: str


@dataclass(frozen=True, slots=True)
class GenderConfig:
    """Configuration for a grammatical gender."""
    id: str
    label: str
    short: str  # Single letter abbreviation


@dataclass(frozen=True, slots=True)
class NumberConfig:
    """Configuration for grammatical number."""
    id: str
    label: str


@dataclass(slots=True)
class GrammarConfig:
    """Language grammar configuration for frontend."""
    cases: list[CaseConfig] = field(default_factory=list)
    genders: list[GenderConfig] = field(default_factory=list)
    numbers: list[NumberConfig] = field(default_factory=list)
    has_declension: bool = False
    has_conjugation: bool = False

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            "cases": [
                {"id": c.id, "label": c.label, "hint": c.hint,
                 "color": {"bg": c.color_bg, "text": c.color_text, "border": c.color_border}}
                for c in self.cases
            ],
            "genders": [{"id": g.id, "label": g.label, "short": g.short} for g in self.genders],
            "numbers": [{"id": n.id, "label": n.label} for n in self.numbers],
            "hasDeclension": self.has_declension,
            "hasConjugation": self.has_conjugation,
        }


class MorphologyEngine(Protocol):
    """Protocol for morphology engines."""
    def analyze(self, word: str) -> list[dict]: ...
    def generate(self, lemma: str, **kwargs) -> list[dict]: ...
    def get_paradigm(self, lemma: str) -> list[dict]: ...


class LanguageModule(ABC):
    """Abstract base for language-specific functionality."""

    @property
    @abstractmethod
    def code(self) -> str:
        """ISO 639-1 language code (e.g., 'ru', 'es')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable language name."""
        ...

    @property
    @abstractmethod
    def native_name(self) -> str:
        """Language name in the language itself."""
        ...

    @abstractmethod
    def get_grammar_config(self) -> GrammarConfig:
        """Get grammar configuration for frontend."""
        ...

    @abstractmethod
    def get_distractors(self, target_lang: str, level: int) -> list[str]:
        """Get distractor words for exercises.
        
        Args:
            target_lang: Language of distractors ('ru' for Russian words, 'en' for English)
            level: Difficulty level (1-3)
        """
        ...

    @abstractmethod
    def build_distractor_pool(self, exclude: list[str], lang: str) -> list[str]:
        """Build pool of distractor words excluding given vocabulary."""
        ...

    @abstractmethod
    def get_morphology_engine(self) -> Any:
        """Get the morphology engine for this language."""
        ...

    def get_declension_patterns(self) -> dict:
        """Get declension patterns for pattern-based exercises. Override if language has declension."""
        return {}

    def get_ending_distractors(self, case: str) -> list[str]:
        """Get distractor endings for pattern exercises. Override if language has declension."""
        return []

    def generate_form(self, lemma: str, case: str, number: str = "singular") -> str | None:
        """Generate inflected form. Override if language has morphology."""
        return None
