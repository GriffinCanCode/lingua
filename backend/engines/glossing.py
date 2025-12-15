"""Interlinear Glossing Engine

Generates Leipzig-style morpheme-by-morpheme breakdowns.
"""
from typing import Optional

try:
    import pymorphy2
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False


# Leipzig glossing abbreviations
GLOSS_ABBREVIATIONS = {
    # Cases
    "nomn": "NOM",
    "gent": "GEN",
    "datv": "DAT",
    "accs": "ACC",
    "ablt": "INS",
    "loct": "LOC",
    # Number
    "sing": "SG",
    "plur": "PL",
    # Gender
    "masc": "M",
    "femn": "F",
    "neut": "N",
    # Person
    "1per": "1",
    "2per": "2",
    "3per": "3",
    # Tense/Aspect
    "pres": "PRS",
    "past": "PST",
    "futr": "FUT",
    "perf": "PFV",
    "impf": "IPFV",
    # Other
    "indc": "IND",
    "impr": "IMP",
    "infn": "INF",
    "prtf": "PTCP",
    "prts": "PTCP.SHORT",
}


class GlossingEngine:
    """Engine for interlinear glossing"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = None
        
        if language == "ru" and PYMORPHY_AVAILABLE:
            self._morph = pymorphy2.MorphAnalyzer()
    
    def segment_word(self, word: str) -> list[dict]:
        """Segment a word into morphemes with glosses"""
        if not self._morph:
            return [{
                "word_index": 0,
                "morpheme_index": 0,
                "surface_form": word,
                "gloss": word.upper(),
                "morpheme_type": "root",
                "lemma": word,
            }]
        
        parses = self._morph.parse(word)
        if not parses:
            return [{
                "word_index": 0,
                "morpheme_index": 0,
                "surface_form": word,
                "gloss": word.upper(),
                "morpheme_type": "root",
                "lemma": word,
            }]
        
        p = parses[0]
        morphemes = []
        
        # Get the lemma/stem
        lemma = p.normal_form
        
        # Build gloss from grammatical features
        gloss_parts = [lemma.upper()]  # Start with lemma meaning
        
        for grammeme in p.tag.grammemes:
            if grammeme in GLOSS_ABBREVIATIONS:
                gloss_parts.append(GLOSS_ABBREVIATIONS[grammeme])
        
        # Simple morpheme breakdown (stem + ending)
        # Real implementation would use morpheme dictionaries
        if len(word) > len(lemma):
            # Has an ending
            # Approximate stem (may not be exact)
            common_len = 0
            for i, (c1, c2) in enumerate(zip(word, lemma)):
                if c1 == c2:
                    common_len = i + 1
                else:
                    break
            
            stem = word[:common_len] if common_len > 0 else word[:-2]
            ending = word[common_len:] if common_len > 0 else word[-2:]
            
            morphemes.append({
                "word_index": 0,
                "morpheme_index": 0,
                "surface_form": stem,
                "gloss": lemma.upper(),
                "morpheme_type": "stem",
                "lemma": lemma,
            })
            
            if ending:
                ending_gloss = ".".join(gloss_parts[1:]) if len(gloss_parts) > 1 else "INFL"
                morphemes.append({
                    "word_index": 0,
                    "morpheme_index": 1,
                    "surface_form": ending,
                    "gloss": ending_gloss,
                    "morpheme_type": "suffix",
                    "lemma": None,
                })
        else:
            # No obvious ending
            morphemes.append({
                "word_index": 0,
                "morpheme_index": 0,
                "surface_form": word,
                "gloss": ".".join(gloss_parts),
                "morpheme_type": "root",
                "lemma": lemma,
            })
        
        return morphemes
    
    def gloss_text(self, text: str) -> list[dict]:
        """Generate glosses for all words in text"""
        words = text.split()
        result = []
        
        for word_idx, word in enumerate(words):
            # Remove punctuation for analysis
            clean_word = word.strip(".,!?;:\"'()-")
            if not clean_word:
                continue
            
            morphemes = self.segment_word(clean_word)
            
            # Update word indices
            for m in morphemes:
                m["word_index"] = word_idx
            
            # Build full gloss for the word
            full_gloss = "-".join(m["gloss"] for m in morphemes)
            
            result.append({
                "word": word,
                "morphemes": morphemes,
                "full_gloss": full_gloss,
            })
        
        return result
    
    def get_interlinear(self, text: str, include_translation: bool = True) -> dict:
        """Get interlinear format for a sentence"""
        glossed = self.gloss_text(text)
        
        original = [g["word"] for g in glossed]
        morpheme_line = ["-".join(m["surface_form"] for m in g["morphemes"]) for g in glossed]
        gloss_line = [g["full_gloss"] for g in glossed]
        
        result = {
            "original": original,
            "morphemes": morpheme_line,
            "glosses": gloss_line,
            "translation": None,
        }
        
        return result
    
    def format_as_interlinear(self, text: str, morphemes: list, translation: Optional[str] = None) -> list[dict]:
        """Format text with stored morphemes as interlinear lines"""
        # Split text into sentences
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        
        lines = []
        for sentence in sentences:
            interlinear = self.get_interlinear(sentence)
            interlinear["translation"] = translation
            lines.append(interlinear)
        
        return lines

