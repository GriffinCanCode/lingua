"""Shared type definitions for language modules."""
from typing import Literal

# Grammatical categories - language modules define their own valid values
GrammaticalCase = Literal[
    "nominative", "genitive", "dative", "accusative", "instrumental", "prepositional",
    # Future: add cases for other languages as needed
]

GrammaticalNumber = Literal["singular", "plural", "dual"]

Gender = Literal["masculine", "feminine", "neuter", "common"]

TargetLanguage = Literal["ru", "en", "es", "de", "fr"]  # Extensible

LevelType = Literal["intro", "easy", "medium", "hard", "review"]
