"""Russian language module implementation."""
from languages.base import LanguageModule, GrammarConfig
from .morph import RussianMorphologyEngine
from .distractors import DISTRACTORS_RU, DISTRACTORS_EN
from .declension import DECLENSION_PATTERNS, ENDING_DISTRACTORS
from .grammar import RUSSIAN_GRAMMAR_CONFIG
from .maps import CASES


class RussianModule(LanguageModule):
    """Russian language module with full morphological support."""

    __slots__ = ("_morph",)

    def __init__(self):
        self._morph: RussianMorphologyEngine | None = None

    @property
    def code(self) -> str:
        return "ru"

    @property
    def name(self) -> str:
        return "Russian"

    @property
    def native_name(self) -> str:
        return "Русский"

    def get_grammar_config(self) -> GrammarConfig:
        """Get grammar configuration for frontend."""
        return RUSSIAN_GRAMMAR_CONFIG

    def get_distractors(self, target_lang: str, level: int) -> list[str]:
        """Get distractor words for exercises."""
        pool = DISTRACTORS_RU if target_lang == "ru" else DISTRACTORS_EN
        return pool.get(level, pool.get(1, []))

    def build_distractor_pool(self, exclude: list[str], lang: str) -> list[str]:
        """Build pool of distractor words excluding given vocabulary."""
        exclude_lower = {w.lower() for w in exclude}
        base = DISTRACTORS_RU if lang == "ru" else DISTRACTORS_EN
        pool = []
        for words in base.values():
            pool.extend(w for w in words if w.lower() not in exclude_lower)
        return pool

    def get_morphology_engine(self) -> RussianMorphologyEngine:
        """Get the morphology engine (lazy-loaded)."""
        if self._morph is None:
            self._morph = RussianMorphologyEngine()
        return self._morph

    def get_declension_patterns(self) -> dict:
        """Get declension patterns for pattern-based exercises."""
        return DECLENSION_PATTERNS

    def get_ending_distractors(self, case: str) -> list[str]:
        """Get distractor endings for pattern exercises."""
        return ENDING_DISTRACTORS.get(case, ["а", "о", "е", "ы"])

    def generate_form(self, lemma: str, case: str, number: str = "singular") -> str | None:
        """Generate inflected form using morphology engine."""
        return self.get_morphology_engine().generate_form(lemma, case, number)

    def get_cases(self) -> list[str]:
        """Get ordered list of grammatical cases."""
        return CASES
