"""Unit 3 Vocabulary Factory - Aggregates all PoS files into unified vocab."""
from pathlib import Path
from functools import lru_cache
from typing import Iterator
import yaml

VOCAB_DIR = Path(__file__).parent

# PoS file mappings
POS_FILES = {
    "verbs": "verbs.yaml",
    "nouns": "nouns.yaml",
    "adverbs": "adverbs.yaml",
}

META_FILES = {
    "meta": "_meta.yaml",
    "lessons": "_lessons.yaml",
}


def _load_yaml(filepath: Path) -> dict:
    """Load YAML file, return empty dict if not found."""
    if not filepath.exists():
        return {}
    with filepath.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_meta() -> dict:
    """Load unit metadata and grammar notes."""
    return _load_yaml(VOCAB_DIR / META_FILES["meta"])


@lru_cache(maxsize=1)
def get_lessons() -> dict:
    """Load lesson mappings."""
    return _load_yaml(VOCAB_DIR / META_FILES["lessons"])


@lru_cache(maxsize=1)
def get_unit_info() -> dict:
    """Get unit metadata (id, title, description, etc.)."""
    meta = get_meta()
    return meta.get("unit", {})


@lru_cache(maxsize=1)
def get_grammar_notes() -> dict:
    """Get grammar notes/rules."""
    meta = get_meta()
    return meta.get("grammar_notes", {})


def _flatten_vocab(data: dict) -> Iterator[dict]:
    """Flatten nested vocab structure into individual items."""
    for key, value in data.items():
        if isinstance(value, list):
            yield from value
        elif isinstance(value, dict):
            yield from _flatten_vocab(value)


@lru_cache(maxsize=1)
def get_all_vocab() -> list[dict]:
    """Load and merge all vocabulary from PoS files."""
    vocab = []
    for pos, filename in POS_FILES.items():
        data = _load_yaml(VOCAB_DIR / filename)
        for item in _flatten_vocab(data):
            item["_source_pos"] = pos
            vocab.append(item)
    return vocab


@lru_cache(maxsize=1)
def get_vocab_by_id() -> dict[str, dict]:
    """Get vocabulary indexed by ID for O(1) lookup."""
    return {item["id"]: item for item in get_all_vocab()}


def get_vocab(vocab_id: str) -> dict | None:
    """Get single vocab item by ID."""
    return get_vocab_by_id().get(vocab_id)


def get_vocab_by_pos(pos: str) -> list[dict]:
    """Get all vocab items for a specific PoS."""
    return [v for v in get_all_vocab() if v.get("pos") == pos]


def get_vocab_by_source(source: str) -> list[dict]:
    """Get all vocab items from a specific source file."""
    return [v for v in get_all_vocab() if v.get("_source_pos") == source]


def get_vocab_ids() -> list[str]:
    """Get list of all vocab IDs."""
    return list(get_vocab_by_id().keys())


def get_lesson_vocab(lesson_key: str) -> dict:
    """Get vocab IDs for a specific lesson."""
    lessons = get_lessons().get("lessons", {})
    return lessons.get(lesson_key, {})


def clear_cache():
    """Clear all cached data (useful for reloading)."""
    get_meta.cache_clear()
    get_lessons.cache_clear()
    get_unit_info.cache_clear()
    get_grammar_notes.cache_clear()
    get_all_vocab.cache_clear()
    get_vocab_by_id.cache_clear()


__all__ = [
    "get_meta",
    "get_lessons",
    "get_unit_info",
    "get_grammar_notes",
    "get_all_vocab",
    "get_vocab_by_id",
    "get_vocab",
    "get_vocab_by_pos",
    "get_vocab_by_source",
    "get_vocab_ids",
    "get_lesson_vocab",
    "clear_cache",
    "VOCAB_DIR",
    "POS_FILES",
]
