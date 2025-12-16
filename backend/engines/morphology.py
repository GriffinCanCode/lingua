"""Morphological Pattern Recognition Engine - Backward Compatibility

This module re-exports from languages.russian.morph for backward compatibility.
New code should import directly from languages.russian.morph.
"""
# Re-export all from Russian morphology module for backward compatibility
from languages.russian.morph import (
    MorphologyEngine,
    RussianMorphologyEngine,
    MorphAnalysis,
    StemEnding,
    PatternParadigm,
    PYMORPHY_AVAILABLE,
)
from languages.russian.maps import (
    CASE_MAP,
    CASE_MAP_REV,
    NUMBER_MAP,
    NUMBER_MAP_REV,
    GENDER_MAP,
    GENDER_MAP_REV,
    POS_MAP,
)
from languages.russian.declension import (
    DECLENSION_PATTERNS,
    ENDING_DISTRACTORS,
)

__all__ = [
    "MorphologyEngine",
    "RussianMorphologyEngine",
    "MorphAnalysis",
    "StemEnding",
    "PatternParadigm",
    "PYMORPHY_AVAILABLE",
    "CASE_MAP",
    "CASE_MAP_REV",
    "NUMBER_MAP",
    "NUMBER_MAP_REV",
    "GENDER_MAP",
    "GENDER_MAP_REV",
    "POS_MAP",
    "DECLENSION_PATTERNS",
    "ENDING_DISTRACTORS",
]
