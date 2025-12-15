"""Interlinear Glossing Engine with Result Types

Generates Leipzig-style morpheme-by-morpheme breakdowns
with monadic error handling.
"""
from dataclasses import dataclass

from core.logging import engine_logger
from core.errors import (
    AppError,
    Ok,
    Err,
    Result,
    internal_error,
)

log = engine_logger()

try:
    import pymorphy2
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False


GLOSS_ABBREVIATIONS = {
    "nomn": "NOM", "gent": "GEN", "datv": "DAT", "accs": "ACC", "ablt": "INS", "loct": "LOC",
    "sing": "SG", "plur": "PL",
    "masc": "M", "femn": "F", "neut": "N",
    "1per": "1", "2per": "2", "3per": "3",
    "pres": "PRS", "past": "PST", "futr": "FUT", "perf": "PFV", "impf": "IPFV",
    "indc": "IND", "impr": "IMP", "infn": "INF", "prtf": "PTCP", "prts": "PTCP.SHORT",
}


@dataclass(frozen=True, slots=True)
class MorphemeData:
    """Single morpheme annotation."""
    word_index: int
    morpheme_index: int
    surface_form: str
    gloss: str
    morpheme_type: str
    lemma: str | None


class GlossingEngine:
    """Engine for interlinear glossing."""
    
    __slots__ = ("language", "_morph")
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = pymorphy2.MorphAnalyzer() if language == "ru" and PYMORPHY_AVAILABLE else None
    
    def segment_word(self, word: str) -> list[dict]:
        """Segment a word into morphemes with glosses."""
        if not self._morph:
            return [{"word_index": 0, "morpheme_index": 0, "surface_form": word, 
                     "gloss": word.upper(), "morpheme_type": "root", "lemma": word}]
        
        parses = self._morph.parse(word)
        if not parses:
            return [{"word_index": 0, "morpheme_index": 0, "surface_form": word,
                     "gloss": word.upper(), "morpheme_type": "root", "lemma": word}]
        
        p = parses[0]
        lemma = p.normal_form
        
        # Build gloss from features
        gloss_parts = [lemma.upper()]
        for grammeme in p.tag.grammemes:
            if grammeme in GLOSS_ABBREVIATIONS:
                gloss_parts.append(GLOSS_ABBREVIATIONS[grammeme])
        
        # Simple morpheme breakdown
        if len(word) > len(lemma):
            common_len = 0
            for i, (c1, c2) in enumerate(zip(word, lemma)):
                if c1 == c2:
                    common_len = i + 1
                else:
                    break
            
            stem = word[:common_len] if common_len > 0 else word[:-2]
            ending = word[common_len:] if common_len > 0 else word[-2:]
            
            morphemes = [{"word_index": 0, "morpheme_index": 0, "surface_form": stem,
                         "gloss": lemma.upper(), "morpheme_type": "stem", "lemma": lemma}]
            
            if ending:
                ending_gloss = ".".join(gloss_parts[1:]) if len(gloss_parts) > 1 else "INFL"
                morphemes.append({"word_index": 0, "morpheme_index": 1, "surface_form": ending,
                                 "gloss": ending_gloss, "morpheme_type": "suffix", "lemma": None})
            return morphemes
        
        return [{"word_index": 0, "morpheme_index": 0, "surface_form": word,
                 "gloss": ".".join(gloss_parts), "morpheme_type": "root", "lemma": lemma}]
    
    def segment_word_result(self, word: str) -> Result[list[MorphemeData], AppError]:
        """Segment with Result type."""
        try:
            morphemes = self.segment_word(word)
            return Ok([MorphemeData(**m) for m in morphemes])
        except Exception as e:
            return internal_error(f"Word segmentation failed: {e}", origin="glossing_engine", cause=e)
    
    def gloss_text(self, text: str) -> list[dict]:
        """Generate glosses for all words in text."""
        result = []
        for word_idx, word in enumerate(text.split()):
            clean = word.strip(".,!?;:\"'()-")
            if not clean:
                continue
            
            morphemes = self.segment_word(clean)
            for m in morphemes:
                m["word_index"] = word_idx
            
            result.append({
                "word": word,
                "morphemes": morphemes,
                "full_gloss": "-".join(m["gloss"] for m in morphemes),
            })
        return result
    
    def get_interlinear(self, text: str, include_translation: bool = True) -> dict:
        """Get interlinear format for a sentence."""
        glossed = self.gloss_text(text)
        return {
            "original": [g["word"] for g in glossed],
            "morphemes": ["-".join(m["surface_form"] for m in g["morphemes"]) for g in glossed],
            "glosses": [g["full_gloss"] for g in glossed],
            "translation": None,
        }
    
    def format_as_interlinear(self, text: str, morphemes: list, translation: str | None = None) -> list[dict]:
        """Format text with stored morphemes as interlinear lines."""
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        lines = []
        for sentence in (s.strip() for s in sentences if s.strip()):
            interlinear = self.get_interlinear(sentence)
            interlinear["translation"] = translation
            lines.append(interlinear)
        return lines
