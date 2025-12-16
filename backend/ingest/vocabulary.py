"""Vocabulary Loader

Loads vocabulary sheets from YAML files and provides:
- Vocabulary by unit
- Vocabulary by lesson
- Review vocabulary (from previous lessons)
- Distractor pools
"""
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache

import yaml


VOCAB_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary"


@dataclass(slots=True)
class VocabEntry:
    """Single vocabulary entry with all metadata."""
    id: str
    word: str
    translation: str
    transliteration: str = ""
    pos: str = ""
    gender: str | None = None
    frequency: int = 2
    difficulty: int = 1
    audio: str | None = None
    notes: str = ""
    examples: list[dict] = field(default_factory=list)
    conjugation: dict | None = None
    register: str | None = None


@dataclass(slots=True)
class LessonVocab:
    """Vocabulary organized for a specific lesson."""
    title: str
    focus: str
    primary: list[VocabEntry]
    secondary: list[VocabEntry]
    review: list[VocabEntry]


@dataclass(slots=True)
class UnitVocab:
    """All vocabulary for a unit."""
    id: str
    title: str
    description: str
    total_words: int
    all_vocab: list[VocabEntry]
    by_section: dict[str, list[VocabEntry]]
    by_lesson: dict[str, LessonVocab]


class VocabularyLoader:
    """Load and manage vocabulary from YAML sheets."""

    __slots__ = ('_cache',)

    def __init__(self):
        self._cache: dict[str, UnitVocab] = {}

    def load_unit(self, unit_id: str) -> UnitVocab | None:
        """Load vocabulary for a specific unit."""
        if unit_id in self._cache:
            return self._cache[unit_id]

        # Find the unit file
        for yaml_file in VOCAB_DIR.glob("*.yaml"):
            if unit_id in yaml_file.stem:
                unit = self._parse_unit_file(yaml_file)
                if unit:
                    self._cache[unit_id] = unit
                    return unit

        return None

    def _parse_unit_file(self, path: Path) -> UnitVocab | None:
        """Parse a unit vocabulary YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "unit" not in data:
            return None

        unit_info = data["unit"]
        all_vocab: list[VocabEntry] = []
        by_section: dict[str, list[VocabEntry]] = {}

        # Parse each section
        sections = [
            "pronouns", "questions", "particles", "location",
            "greetings", "cognates", "nouns", "possession",
            "descriptors", "numbers", "colors", "verbs",
            "food_drink", "time", "phrases"
        ]

        for section in sections:
            if section not in data:
                continue

            section_vocab = []
            for entry in data[section]:
                vocab = self._parse_entry(entry)
                section_vocab.append(vocab)
                all_vocab.append(vocab)

            by_section[section] = section_vocab

        # Parse lesson mappings
        by_lesson: dict[str, LessonVocab] = {}
        lessons_data = data.get("lessons", {})
        vocab_by_id = {v.id: v for v in all_vocab}

        for lesson_key, lesson_data in lessons_data.items():
            primary = [vocab_by_id[vid] for vid in lesson_data.get("primary_vocab", []) if vid in vocab_by_id]
            secondary = [vocab_by_id[vid] for vid in lesson_data.get("secondary_vocab", []) if vid in vocab_by_id]
            review = [vocab_by_id[vid] for vid in lesson_data.get("review_vocab", []) if vid in vocab_by_id]

            by_lesson[lesson_key] = LessonVocab(
                title=lesson_data.get("title", ""),
                focus=lesson_data.get("focus", ""),
                primary=primary,
                secondary=secondary,
                review=review,
            )

        return UnitVocab(
            id=unit_info.get("id", ""),
            title=unit_info.get("title", ""),
            description=unit_info.get("description", ""),
            total_words=len(all_vocab),
            all_vocab=all_vocab,
            by_section=by_section,
            by_lesson=by_lesson,
        )

    def _parse_entry(self, data: dict) -> VocabEntry:
        """Parse a single vocabulary entry."""
        return VocabEntry(
            id=data.get("id", ""),
            word=data.get("word", ""),
            translation=data.get("translation", ""),
            transliteration=data.get("transliteration", ""),
            pos=data.get("pos", ""),
            gender=data.get("gender"),
            frequency=data.get("frequency", 2),
            difficulty=data.get("difficulty", 1),
            audio=data.get("audio"),
            notes=data.get("notes", ""),
            examples=data.get("examples", []),
            conjugation=data.get("conjugation"),
            register=data.get("register"),
        )

    def get_lesson_vocab(self, unit_id: str, lesson_key: str) -> LessonVocab | None:
        """Get vocabulary for a specific lesson."""
        unit = self.load_unit(unit_id)
        if not unit:
            return None
        return unit.by_lesson.get(lesson_key)

    def get_review_vocab(self, unit_id: str, lesson_key: str, max_items: int = 10) -> list[VocabEntry]:
        """Get review vocabulary from previous lessons in the unit."""
        unit = self.load_unit(unit_id)
        if not unit:
            return []

        lesson_keys = list(unit.by_lesson.keys())
        try:
            current_idx = lesson_keys.index(lesson_key)
        except ValueError:
            return []

        # Collect vocab from all previous lessons
        review_pool: list[VocabEntry] = []
        for prev_key in lesson_keys[:current_idx]:
            prev_lesson = unit.by_lesson.get(prev_key)
            if prev_lesson:
                review_pool.extend(prev_lesson.primary)

        # Sort by frequency (most important first) and limit
        review_pool.sort(key=lambda v: v.frequency)
        return review_pool[:max_items]

    def get_distractor_pool(self, unit_id: str, exclude: list[str], language: str = "ru") -> list[str]:
        """Get words for distractors, excluding specified words."""
        unit = self.load_unit(unit_id)
        if not unit:
            return []

        exclude_lower = {w.lower() for w in exclude}

        if language == "ru":
            words = [v.word for v in unit.all_vocab if v.word.lower() not in exclude_lower]
        else:
            words = [v.translation for v in unit.all_vocab if v.translation.lower() not in exclude_lower]

        return words

    def vocab_to_dict(self, vocab: VocabEntry) -> dict:
        """Convert VocabEntry to dict for API/exercise generation."""
        return {
            "word": vocab.word,
            "translation": vocab.translation,
            "audio": vocab.audio,
            "hints": [vocab.notes] if vocab.notes else [],
            "gender": vocab.gender,
            "transliteration": vocab.transliteration,
        }

    def lesson_vocab_to_dicts(self, lesson: LessonVocab) -> tuple[list[dict], list[dict]]:
        """Convert lesson vocab to dicts (primary, review)."""
        primary = [self.vocab_to_dict(v) for v in lesson.primary + lesson.secondary]
        review = [self.vocab_to_dict(v) for v in lesson.review]
        return primary, review


# Singleton instance
_loader: VocabularyLoader | None = None


def get_vocabulary_loader() -> VocabularyLoader:
    """Get the singleton vocabulary loader."""
    global _loader
    if _loader is None:
        _loader = VocabularyLoader()
    return _loader


def get_lesson_vocabulary(unit_id: str, lesson_key: str) -> tuple[list[dict], list[dict]]:
    """Convenience function to get lesson vocabulary as dicts."""
    loader = get_vocabulary_loader()
    lesson = loader.get_lesson_vocab(unit_id, lesson_key)
    if not lesson:
        return [], []
    return loader.lesson_vocab_to_dicts(lesson)
