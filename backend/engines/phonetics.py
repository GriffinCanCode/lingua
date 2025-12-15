"""Phonetics Engine

Provides phonological analysis, minimal pair generation, and acoustic feedback.
Uses librosa for audio processing when available.
"""
from typing import Optional
import os

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


# Russian phoneme inventory and IPA mappings
RUSSIAN_IPA = {
    "а": "a", "о": "o", "у": "u", "э": "ɛ", "ы": "ɨ", "и": "i",
    "я": "ja", "ё": "jo", "ю": "ju", "е": "jɛ",
    "б": "b", "в": "v", "г": "g", "д": "d", "ж": "ʐ", "з": "z",
    "к": "k", "л": "l", "м": "m", "н": "n", "п": "p", "р": "r",
    "с": "s", "т": "t", "ф": "f", "х": "x", "ц": "t͡s", "ч": "t͡ɕ",
    "ш": "ʂ", "щ": "ɕː", "й": "j",
    "ь": "ʲ", "ъ": "",
}

# Phonological contrasts learners need to master
RUSSIAN_CONTRASTS = [
    {
        "contrast": "ы/и",
        "description": "Back unrounded vs front unrounded high vowel",
        "difficulty": "high",
        "examples": [("мыло", "мила"), ("быть", "бить"), ("выл", "вил")],
    },
    {
        "contrast": "palatalized/non-palatalized",
        "description": "Consonant palatalization contrast",
        "difficulty": "high",
        "examples": [("мат", "мать"), ("кон", "конь"), ("брат", "брать")],
    },
    {
        "contrast": "ш/щ",
        "description": "Retroflex vs palatal sibilant",
        "difficulty": "medium",
        "examples": [("шить", "щит"), ("каша", "чаща")],
    },
    {
        "contrast": "voiced/voiceless",
        "description": "Voicing distinction in consonants",
        "difficulty": "low",
        "examples": [("бар", "пар"), ("дом", "том"), ("год", "кот")],
    },
    {
        "contrast": "hard/soft л",
        "description": "Dark vs light lateral",
        "difficulty": "medium",
        "examples": [("мол", "моль"), ("был", "быль"), ("угол", "уголь")],
    },
]

# Minimal pairs database
RUSSIAN_MINIMAL_PAIRS = [
    {"word1": "мыло", "word2": "мила", "ipa1": "ˈmɨlə", "ipa2": "ˈmʲilə", "contrast": "ы/и", "description": "soap vs. dear (fem)"},
    {"word1": "быть", "word2": "бить", "ipa1": "bɨtʲ", "ipa2": "bʲitʲ", "contrast": "ы/и", "description": "to be vs. to beat"},
    {"word1": "мат", "word2": "мать", "ipa1": "mat", "ipa2": "matʲ", "contrast": "palatalized/non-palatalized", "description": "checkmate vs. mother"},
    {"word1": "брат", "word2": "брать", "ipa1": "brat", "ipa2": "bratʲ", "contrast": "palatalized/non-palatalized", "description": "brother vs. to take"},
    {"word1": "угол", "word2": "уголь", "ipa1": "ˈugəl", "ipa2": "ˈugəlʲ", "contrast": "hard/soft л", "description": "corner vs. coal"},
    {"word1": "бар", "word2": "пар", "ipa1": "bar", "ipa2": "par", "contrast": "voiced/voiceless", "description": "bar vs. steam"},
    {"word1": "дом", "word2": "том", "ipa1": "dom", "ipa2": "tom", "contrast": "voiced/voiceless", "description": "house vs. volume"},
    {"word1": "шить", "word2": "щит", "ipa1": "ʂɨtʲ", "ipa2": "ɕːit", "contrast": "ш/щ", "description": "to sew vs. shield"},
]


class PhoneticsEngine:
    """Engine for phonological analysis and training"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
    
    def get_ipa(self, word: str) -> str:
        """Get IPA transcription for a word"""
        if self.language != "ru":
            return word  # Only Russian supported for now
        
        ipa = []
        for char in word.lower():
            if char in RUSSIAN_IPA:
                ipa.append(RUSSIAN_IPA[char])
            else:
                ipa.append(char)
        
        return "".join(ipa)
    
    def analyze_phonemes(self, word: str) -> dict:
        """Analyze phonemes in a word"""
        ipa = self.get_ipa(word)
        
        # Simple syllabification (placeholder - real impl would use rules)
        syllables = [word]  # Simplified
        
        return {
            "word": word,
            "ipa": ipa,
            "phonemes": list(ipa),
            "syllables": syllables,
            "stress_position": None,  # Would need stress dictionary
        }
    
    def get_minimal_pairs(self, contrast: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Get minimal pairs for practice"""
        pairs = RUSSIAN_MINIMAL_PAIRS
        
        if contrast:
            pairs = [p for p in pairs if p["contrast"] == contrast]
        
        return pairs[:limit]
    
    def get_contrasts(self) -> list[dict]:
        """Get phonological contrasts for the language"""
        return RUSSIAN_CONTRASTS
    
    def analyze_audio(self, audio_path: str) -> dict:
        """Analyze acoustic features of audio file"""
        if not LIBROSA_AVAILABLE:
            return {
                "duration_ms": 0,
                "f0_mean": None,
                "f0_range": None,
                "formants": None,
                "error": "librosa not available",
            }
        
        try:
            y, sr = librosa.load(audio_path)
            duration_ms = len(y) / sr * 1000
            
            # Extract F0 (pitch)
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')
            )
            f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([])
            
            f0_mean = float(np.mean(f0_clean)) if len(f0_clean) > 0 else None
            f0_range = (float(np.min(f0_clean)), float(np.max(f0_clean))) if len(f0_clean) > 0 else None
            
            # Simple formant estimation (placeholder - real impl would use LPC)
            formants = None
            
            return {
                "duration_ms": duration_ms,
                "f0_mean": f0_mean,
                "f0_range": f0_range,
                "formants": formants,
            }
        except Exception as e:
            return {
                "duration_ms": 0,
                "f0_mean": None,
                "f0_range": None,
                "formants": None,
                "error": str(e),
            }
    
    def compare_pronunciation(self, target_word: str, audio_path: str) -> dict:
        """Compare user pronunciation to target"""
        target_ipa = self.get_ipa(target_word)
        
        # Analyze user audio
        audio_features = self.analyze_audio(audio_path)
        
        # Placeholder for actual comparison
        # Real implementation would use DTW, acoustic model, etc.
        return {
            "target_word": target_word,
            "target_ipa": target_ipa,
            "user_ipa": target_ipa,  # Placeholder
            "accuracy_score": 0.8,  # Placeholder
            "specific_errors": [],
            "suggestions": ["Practice the ы sound more"],
        }

