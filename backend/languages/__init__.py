"""Language modules for multi-language support.

Provides factory/registry pattern for language-specific functionality.
"""
from .registry import get_module, register, list_languages
from .base import LanguageModule, GrammarConfig
from .types import GrammaticalCase, GrammaticalNumber, Gender

__all__ = [
    "get_module",
    "register",
    "list_languages",
    "LanguageModule",
    "GrammarConfig",
    "GrammaticalCase",
    "GrammaticalNumber",
    "Gender",
]
