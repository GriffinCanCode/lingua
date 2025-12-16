"""Vocabulary Loader

Loads vocabulary from modular YAML files via unit factories.
Provides:
- Vocabulary by unit
- Vocabulary by lesson
- Review vocabulary (from previous lessons)
- Distractor pools
"""
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterator
import importlib
import yaml

CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content"


def _get_unit_module(language: str, unit_folder: str):
    """Dynamically import unit vocab module."""
    module_path = f"data.content.{language}.{unit_folder}.vocab"
    return importlib.import_module(module_path)


def get_vocab_dirs(language: str = "ru") -> list[Path]:
    """Get all vocabulary directories for a language (one per unit)."""
    lang_dir = CONTENT_DIR / language
    if not lang_dir.exists():
        return []
    return sorted([d / "vocab" for d in lang_dir.iterdir() if d.is_dir() and (d / "vocab").exists()])


@dataclass(slots=True)
class VocabEntry:
    """Single vocabulary entry with all metadata."""
    id: str
    word: str
    translation: str
    stressed: str = ""
    transliteration: str = ""
    pos: str = ""
    gender: str | None = None
    semantic: list[str] = field(default_factory=list)
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
    by_pos: dict[str, list[VocabEntry]]
    by_lesson: dict[str, LessonVocab]


class VocabularyLoader:
    """Load and manage vocabulary from modular YAML factories."""

    __slots__ = ('_cache', '_language')

    def __init__(self, language: str = "ru"):
        self._cache: dict[str, UnitVocab] = {}
        self._language = language

    def _unit_folder_to_id(self, folder: str) -> str:
        """Map folder name to unit ID."""
        mapping = {"unit_one": "unit1", "unit_two": "unit2", "unit_three": "unit3"}
        return mapping.get(folder, folder)

    def _unit_id_to_folder(self, unit_id: str) -> str:
        """Map unit ID to folder name."""
        mapping = {"unit1": "unit_one", "unit2": "unit_two", "unit3": "unit_three"}
        return mapping.get(unit_id, unit_id)

    def load_unit(self, unit_id: str) -> UnitVocab | None:
        """Load vocabulary for a specific unit."""
        if unit_id in self._cache:
            return self._cache[unit_id]

        folder = self._unit_id_to_folder(unit_id)
        try:
            module = _get_unit_module(self._language, folder)
        except ImportError:
            return None

        unit_info = module.get_unit_info()
        if not unit_info:
            return None

        all_vocab_dicts = module.get_all_vocab()
        all_vocab = [self._parse_entry(v) for v in all_vocab_dicts]
        vocab_by_id = {v.id: v for v in all_vocab}

        # Group by PoS
        by_pos: dict[str, list[VocabEntry]] = {}
        for v in all_vocab:
            by_pos.setdefault(v.pos, []).append(v)

        # Build lesson vocab
        by_lesson: dict[str, LessonVocab] = {}
        lessons_data = module.get_lessons().get("lessons", {})

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

        result = UnitVocab(
            id=unit_info.get("id", unit_id),
            title=unit_info.get("title", ""),
            description=unit_info.get("description", ""),
            total_words=len(all_vocab),
            all_vocab=all_vocab,
            by_pos=by_pos,
            by_lesson=by_lesson,
        )
        self._cache[unit_id] = result
        return result

    def _parse_entry(self, data: dict) -> VocabEntry:
        """Parse a single vocabulary entry from dict."""
        return VocabEntry(
            id=data.get("id", ""),
            word=data.get("word", ""),
            translation=data.get("translation", ""),
            stressed=data.get("stressed", ""),
            transliteration=data.get("transliteration", ""),
            pos=data.get("pos", ""),
            gender=data.get("gender"),
            semantic=data.get("semantic", []),
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
        return unit.by_lesson.get(lesson_key) if unit else None

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

        review_pool: list[VocabEntry] = []
        for prev_key in lesson_keys[:current_idx]:
            prev_lesson = unit.by_lesson.get(prev_key)
            if prev_lesson:
                review_pool.extend(prev_lesson.primary)

        review_pool.sort(key=lambda v: v.frequency)
        return review_pool[:max_items]

    def get_distractor_pool(self, unit_id: str, exclude: list[str], language: str = "ru") -> list[str]:
        """Get words for distractors, excluding specified words."""
        unit = self.load_unit(unit_id)
        if not unit:
            return []

        exclude_lower = {w.lower() for w in exclude}
        if language == "ru":
            return [v.word for v in unit.all_vocab if v.word.lower() not in exclude_lower]
        return [v.translation for v in unit.all_vocab if v.translation.lower() not in exclude_lower]

    def vocab_to_dict(self, vocab: VocabEntry) -> dict:
        """Convert VocabEntry to dict for API/exercise generation."""
        return {
            "id": vocab.id,
            "word": vocab.word,
            "stressed": vocab.stressed,
            "translation": vocab.translation,
            "pos": vocab.pos,
            "audio": vocab.audio,
            "hints": [vocab.notes] if vocab.notes else [],
            "gender": vocab.gender,
            "semantic": vocab.semantic,
            "transliteration": vocab.transliteration,
        }

    def lesson_vocab_to_dicts(self, lesson: LessonVocab) -> tuple[list[dict], list[dict]]:
        """Convert lesson vocab to dicts (primary, review)."""
        primary = [self.vocab_to_dict(v) for v in lesson.primary + lesson.secondary]
        review = [self.vocab_to_dict(v) for v in lesson.review]
        return primary, review


# Singleton instances per language
_loaders: dict[str, VocabularyLoader] = {}


def get_vocabulary_loader(language: str = "ru") -> VocabularyLoader:
    """Get the vocabulary loader for a language."""
    if language not in _loaders:
        _loaders[language] = VocabularyLoader(language)
    return _loaders[language]


def get_lesson_vocabulary(unit_id: str, lesson_key: str, language: str = "ru") -> tuple[list[dict], list[dict]]:
    """Convenience function to get lesson vocabulary as dicts."""
    loader = get_vocabulary_loader(language)
    lesson = loader.get_lesson_vocab(unit_id, lesson_key)
    return loader.lesson_vocab_to_dicts(lesson) if lesson else ([], [])
