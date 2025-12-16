"""Russian Language Vocabulary Factory - Aggregates all units efficiently."""
from pathlib import Path
from functools import lru_cache
from typing import Iterator
import importlib

CONTENT_DIR = Path(__file__).parent

# Unit module mappings - lazy loaded
UNITS = {
    "unit1": "unit_one.vocab",
    "unit2": "unit_two.vocab",
    "unit3": "unit_three.vocab",
}


@lru_cache(maxsize=None)
def _get_unit_module(unit_id: str):
    """Lazy-load unit vocab module."""
    module_path = UNITS.get(unit_id)
    if not module_path:
        raise ValueError(f"Unknown unit: {unit_id}")
    return importlib.import_module(f".{module_path}", package=__name__)


def get_unit(unit_id: str):
    """Get a specific unit's vocab module."""
    return _get_unit_module(unit_id)


def get_unit_ids() -> list[str]:
    """Get list of available unit IDs."""
    return list(UNITS.keys())


@lru_cache(maxsize=1)
def get_all_units_info() -> dict[str, dict]:
    """Get metadata for all units."""
    return {uid: _get_unit_module(uid).get_unit_info() for uid in UNITS}


def get_unit_vocab(unit_id: str) -> list[dict]:
    """Get all vocab for a specific unit."""
    return _get_unit_module(unit_id).get_all_vocab()


def get_unit_vocab_by_id(unit_id: str) -> dict[str, dict]:
    """Get vocab indexed by ID for a specific unit."""
    return _get_unit_module(unit_id).get_vocab_by_id()


@lru_cache(maxsize=1)
def get_all_vocab() -> list[dict]:
    """Get all vocabulary across all units (with unit_id tagged)."""
    vocab = []
    for unit_id in UNITS:
        unit_vocab = get_unit_vocab(unit_id)
        for item in unit_vocab:
            item["_unit"] = unit_id
            vocab.append(item)
    return vocab


@lru_cache(maxsize=1)
def get_all_vocab_by_id() -> dict[str, dict]:
    """Get all vocabulary indexed by ID across all units.
    
    Note: If duplicate IDs exist across units, later units override earlier.
    Use get_vocab_with_unit() for unit-specific lookup.
    """
    return {item["id"]: item for item in get_all_vocab()}


def get_vocab(vocab_id: str) -> dict | None:
    """Get single vocab item by ID (searches all units)."""
    return get_all_vocab_by_id().get(vocab_id)


def get_vocab_with_unit(vocab_id: str, unit_id: str) -> dict | None:
    """Get vocab item by ID from specific unit."""
    return _get_unit_module(unit_id).get_vocab(vocab_id)


def get_vocab_by_pos(pos: str, unit_id: str | None = None) -> list[dict]:
    """Get vocab items by PoS, optionally filtered by unit."""
    if unit_id:
        return _get_unit_module(unit_id).get_vocab_by_pos(pos)
    return [v for v in get_all_vocab() if v.get("pos") == pos]


def get_vocab_ids(unit_id: str | None = None) -> list[str]:
    """Get list of vocab IDs, optionally filtered by unit."""
    if unit_id:
        return _get_unit_module(unit_id).get_vocab_ids()
    return list(get_all_vocab_by_id().keys())


def get_lesson_vocab(unit_id: str, lesson_key: str) -> dict:
    """Get vocab IDs for a specific lesson in a unit."""
    return _get_unit_module(unit_id).get_lesson_vocab(lesson_key)


def get_unit_lessons(unit_id: str) -> dict:
    """Get all lessons for a unit."""
    return _get_unit_module(unit_id).get_lessons()


def search_vocab(query: str, field: str = "word") -> list[dict]:
    """Search vocab by field value (case-insensitive substring match)."""
    query_lower = query.lower()
    return [
        v for v in get_all_vocab()
        if query_lower in str(v.get(field, "")).lower()
    ]


def get_vocab_stats() -> dict:
    """Get vocabulary statistics across all units."""
    all_vocab = get_all_vocab()
    pos_counts = {}
    unit_counts = {}
    
    for v in all_vocab:
        pos = v.get("pos", "unknown")
        unit = v.get("_unit", "unknown")
        pos_counts[pos] = pos_counts.get(pos, 0) + 1
        unit_counts[unit] = unit_counts.get(unit, 0) + 1
    
    return {
        "total": len(all_vocab),
        "by_pos": pos_counts,
        "by_unit": unit_counts,
    }


def clear_all_caches():
    """Clear all cached data across all units."""
    _get_unit_module.cache_clear()
    get_all_units_info.cache_clear()
    get_all_vocab.cache_clear()
    get_all_vocab_by_id.cache_clear()
    
    # Clear individual unit caches
    for unit_id in UNITS:
        try:
            _get_unit_module(unit_id).clear_cache()
        except Exception:
            pass


__all__ = [
    "get_unit",
    "get_unit_ids",
    "get_all_units_info",
    "get_unit_vocab",
    "get_unit_vocab_by_id",
    "get_all_vocab",
    "get_all_vocab_by_id",
    "get_vocab",
    "get_vocab_with_unit",
    "get_vocab_by_pos",
    "get_vocab_ids",
    "get_lesson_vocab",
    "get_unit_lessons",
    "search_vocab",
    "get_vocab_stats",
    "clear_all_caches",
    "CONTENT_DIR",
    "UNITS",
]
