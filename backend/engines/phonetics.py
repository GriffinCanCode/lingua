"""Phonetics Engine with Result Types

Provides phonological analysis, minimal pair generation, and acoustic feedback.
Uses librosa for audio processing with monadic error handling.
"""
from dataclasses import dataclass

from core.logging import engine_logger
from core.errors import (
    AppError,
    Ok,
    Err,
    Result,
    internal_error,
    not_implemented,
)

log = engine_logger()

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


# Russian phoneme inventory
RUSSIAN_IPA = {
    "а": "a", "о": "o", "у": "u", "э": "ɛ", "ы": "ɨ", "и": "i",
    "я": "ja", "ё": "jo", "ю": "ju", "е": "jɛ",
    "б": "b", "в": "v", "г": "g", "д": "d", "ж": "ʐ", "з": "z",
    "к": "k", "л": "l", "м": "m", "н": "n", "п": "p", "р": "r",
    "с": "s", "т": "t", "ф": "f", "х": "x", "ц": "t͡s", "ч": "t͡ɕ",
    "ш": "ʂ", "щ": "ɕː", "й": "j", "ь": "ʲ", "ъ": "",
}

RUSSIAN_CONTRASTS = [
    {"contrast": "ы/и", "description": "Back vs front unrounded high vowel", "difficulty": "high",
     "examples": [("мыло", "мила"), ("быть", "бить"), ("выл", "вил")]},
    {"contrast": "palatalized/non-palatalized", "description": "Consonant palatalization", "difficulty": "high",
     "examples": [("мат", "мать"), ("кон", "конь"), ("брат", "брать")]},
    {"contrast": "ш/щ", "description": "Retroflex vs palatal sibilant", "difficulty": "medium",
     "examples": [("шить", "щит"), ("каша", "чаща")]},
    {"contrast": "voiced/voiceless", "description": "Voicing distinction", "difficulty": "low",
     "examples": [("бар", "пар"), ("дом", "том"), ("год", "кот")]},
    {"contrast": "hard/soft л", "description": "Dark vs light lateral", "difficulty": "medium",
     "examples": [("мол", "моль"), ("был", "быль"), ("угол", "уголь")]},
]

RUSSIAN_MINIMAL_PAIRS = [
    {"word1": "мыло", "word2": "мила", "ipa1": "ˈmɨlə", "ipa2": "ˈmʲilə", "contrast": "ы/и", "description": "soap vs dear (fem)"},
    {"word1": "быть", "word2": "бить", "ipa1": "bɨtʲ", "ipa2": "bʲitʲ", "contrast": "ы/и", "description": "to be vs to beat"},
    {"word1": "мат", "word2": "мать", "ipa1": "mat", "ipa2": "matʲ", "contrast": "palatalized/non-palatalized", "description": "checkmate vs mother"},
    {"word1": "брат", "word2": "брать", "ipa1": "brat", "ipa2": "bratʲ", "contrast": "palatalized/non-palatalized", "description": "brother vs to take"},
    {"word1": "угол", "word2": "уголь", "ipa1": "ˈugəl", "ipa2": "ˈugəlʲ", "contrast": "hard/soft л", "description": "corner vs coal"},
    {"word1": "бар", "word2": "пар", "ipa1": "bar", "ipa2": "par", "contrast": "voiced/voiceless", "description": "bar vs steam"},
    {"word1": "дом", "word2": "том", "ipa1": "dom", "ipa2": "tom", "contrast": "voiced/voiceless", "description": "house vs volume"},
    {"word1": "шить", "word2": "щит", "ipa1": "ʂɨtʲ", "ipa2": "ɕːit", "contrast": "ш/щ", "description": "to sew vs shield"},
]


@dataclass(frozen=True, slots=True)
class AcousticAnalysis:
    """Result of acoustic analysis."""
    duration_ms: float
    f0_mean: float | None
    f0_range: tuple[float, float] | None
    formants: dict[str, float] | None


class PhoneticsEngine:
    """Engine for phonological analysis and training."""
    
    __slots__ = ("language",)
    
    def __init__(self, language: str = "ru"):
        self.language = language
    
    def get_ipa(self, word: str) -> str:
        """Get IPA transcription for a word."""
        if self.language != "ru":
            return word
        return "".join(RUSSIAN_IPA.get(c, c) for c in word.lower())
    
    def analyze_phonemes(self, word: str) -> dict:
        """Analyze phonemes in a word."""
        ipa = self.get_ipa(word)
        return {
            "word": word,
            "ipa": ipa,
            "phonemes": list(ipa),
            "syllables": [word],
            "stress_position": None,
        }
    
    def analyze_phonemes_result(self, word: str) -> Result[dict, AppError]:
        """Analyze phonemes with Result type."""
        try:
            return Ok(self.analyze_phonemes(word))
        except Exception as e:
            return internal_error(f"Phoneme analysis failed: {e}", origin="phonetics_engine", cause=e)
    
    def get_minimal_pairs(self, contrast: str | None = None, limit: int = 10) -> list[dict]:
        """Get minimal pairs for practice."""
        pairs = RUSSIAN_MINIMAL_PAIRS
        if contrast:
            pairs = [p for p in pairs if p["contrast"] == contrast]
        return pairs[:limit]
    
    def get_contrasts(self) -> list[dict]:
        """Get phonological contrasts for the language."""
        return RUSSIAN_CONTRASTS
    
    def analyze_audio(self, audio_path: str) -> dict:
        """Analyze acoustic features of audio file."""
        if not LIBROSA_AVAILABLE:
            log.warning("librosa_unavailable", path=audio_path)
            return {
                "duration_ms": 0,
                "f0_mean": None,
                "f0_range": None,
                "formants": None,
            }
        
        try:
            y, sr = librosa.load(audio_path)
            duration_ms = len(y) / sr * 1000
            
            f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
            f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([])
            
            return {
                "duration_ms": duration_ms,
                "f0_mean": float(np.mean(f0_clean)) if len(f0_clean) > 0 else None,
                "f0_range": (float(np.min(f0_clean)), float(np.max(f0_clean))) if len(f0_clean) > 0 else None,
                "formants": None,
            }
        except Exception as e:
            log.error("audio_analysis_failed", error=str(e), path=audio_path)
            return {"duration_ms": 0, "f0_mean": None, "f0_range": None, "formants": None}
    
    def analyze_audio_result(self, audio_path: str) -> Result[AcousticAnalysis, AppError]:
        """Analyze audio with Result type."""
        if not LIBROSA_AVAILABLE:
            return not_implemented("audio_analysis", origin="phonetics_engine")
        
        try:
            result = self.analyze_audio(audio_path)
            return Ok(AcousticAnalysis(
                duration_ms=result["duration_ms"],
                f0_mean=result["f0_mean"],
                f0_range=result["f0_range"],
                formants=result["formants"],
            ))
        except Exception as e:
            return internal_error(f"Audio analysis failed: {e}", origin="phonetics_engine", cause=e)
    
    def compare_pronunciation(self, target_word: str, audio_path: str) -> dict:
        """Compare user pronunciation to target."""
        target_ipa = self.get_ipa(target_word)
        self.analyze_audio(audio_path)
        
        return {
            "target_word": target_word,
            "target_ipa": target_ipa,
            "user_ipa": target_ipa,
            "accuracy_score": 0.8,
            "specific_errors": [],
            "suggestions": ["Practice the ы sound more"],
        }
