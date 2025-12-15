"""Etymology Engine with Result Types

Manages etymology graph data and cognate detection
with monadic error handling.
"""
from dataclasses import dataclass

from core.errors import (
    AppError,
    Ok,
    Err,
    Result,
    not_found,
)


@dataclass(frozen=True, slots=True)
class Cognate:
    """Cognate word data."""
    word: str
    language: str
    meaning: str
    is_reconstructed: bool = False


@dataclass(frozen=True, slots=True)
class EtymologyChain:
    """Etymology derivation chain."""
    word: str
    language: str
    period: str
    meaning: str | None = None


SAMPLE_COGNATES = {
    "город": [
        Cognate("grad", "sla", "city (Slavic)"),
        Cognate("gard", "got", "enclosure (Gothic)"),
        Cognate("yard", "en", "enclosed space"),
        Cognate("garden", "en", "enclosed growing space"),
        Cognate("*gʰórdʰos", "pie", "enclosure (Proto-IE)", True),
    ],
    "мать": [
        Cognate("mother", "en", "female parent"),
        Cognate("mater", "la", "mother (Latin)"),
        Cognate("μήτηρ", "grc", "mother (Greek)"),
        Cognate("*méh₂tēr", "pie", "mother (Proto-IE)", True),
    ],
    "вода": [
        Cognate("water", "en", "water"),
        Cognate("Wasser", "de", "water (German)"),
        Cognate("*wódr̥", "pie", "water (Proto-IE)", True),
    ],
}

SAMPLE_CHAINS = {
    "город": [
        EtymologyChain("город", "ru", "Modern Russian"),
        EtymologyChain("городъ", "orv", "Old East Slavic"),
        EtymologyChain("*gordъ", "sla", "Proto-Slavic"),
        EtymologyChain("*gʰórdʰos", "pie", "Proto-Indo-European", "enclosure"),
    ],
}

SAMPLE_FAMILIES = {
    "*gʰórdʰos": {
        "root": "*gʰórdʰos",
        "meaning": "enclosure",
        "descendants": [
            {"word": "город", "language": "ru", "meaning": "city"},
            {"word": "grad", "language": "hr", "meaning": "city"},
            {"word": "gród", "language": "pl", "meaning": "fortified settlement"},
            {"word": "yard", "language": "en", "meaning": "enclosed space"},
            {"word": "garden", "language": "en", "meaning": "enclosed garden"},
            {"word": "Garten", "language": "de", "meaning": "garden"},
        ],
    },
}


class EtymologyEngine:
    """Engine for etymology analysis and cognate detection."""
    
    __slots__ = ("language",)
    
    def __init__(self, language: str = "ru"):
        self.language = language
    
    def find_cognates(self, word: str, source_language: str = "ru") -> list[dict]:
        """Find cognates of a word across languages."""
        cognates = SAMPLE_COGNATES.get(word, [])
        return [
            {"word": c.word, "language": c.language, "meaning": c.meaning, "is_reconstructed": c.is_reconstructed}
            for c in cognates
        ]
    
    def find_cognates_result(self, word: str, source_language: str = "ru") -> Result[list[Cognate], AppError]:
        """Find cognates with Result type."""
        cognates = SAMPLE_COGNATES.get(word)
        if cognates is None:
            return not_found("Cognates", word, origin="etymology_engine")
        return Ok(list(cognates))
    
    def get_etymology_chain(self, word: str, language: str = "ru") -> list[dict]:
        """Get etymological derivation chain for a word."""
        chain = SAMPLE_CHAINS.get(word, [EtymologyChain(word, language, "Unknown")])
        return [{"word": c.word, "language": c.language, "period": c.period, "meaning": c.meaning} for c in chain]
    
    def get_etymology_chain_result(self, word: str, language: str = "ru") -> Result[list[EtymologyChain], AppError]:
        """Get etymology chain with Result type."""
        chain = SAMPLE_CHAINS.get(word)
        if chain is None:
            return Ok([EtymologyChain(word, language, "Unknown")])
        return Ok(list(chain))
    
    def get_word_family(self, root: str, language: str = "pie") -> dict:
        """Get word family derived from a proto-root."""
        return SAMPLE_FAMILIES.get(root, {"root": root, "meaning": "unknown", "descendants": []})
    
    def detect_cognates(self, word1: str, lang1: str, word2: str, lang2: str) -> dict:
        """Detect if two words are cognates."""
        return {
            "word1": word1, "lang1": lang1,
            "word2": word2, "lang2": lang2,
            "is_cognate": False,
            "confidence": 0.0,
            "notes": "Full cognate detection requires sound correspondence database",
        }
