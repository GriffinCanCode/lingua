"""Morphological Pattern Recognition Engine with Result Types

Uses pymorphy3 for Russian morphological analysis and generation.
Provides rule-based explanations with monadic error handling.
"""
from dataclasses import dataclass

from core.logging import engine_logger
from core.errors import (
    AppError,
    ErrorCode,
    Ok,
    Err,
    Result,
    internal_error,
)

log = engine_logger()

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
    log.debug("pymorphy3_loaded", available=True)
except ImportError:
    PYMORPHY_AVAILABLE = False
    log.warning("pymorphy3_unavailable", message="Morphological analysis will be limited")


CASE_MAP = {
    "nomn": "nominative",
    "gent": "genitive",
    "datv": "dative",
    "accs": "accusative",
    "ablt": "instrumental",
    "loct": "prepositional",
}

NUMBER_MAP = {"sing": "singular", "plur": "plural"}

GENDER_MAP = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}

POS_MAP = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJF": "adjective",
    "ADJS": "short_adjective",
    "ADVB": "adverb",
    "PREP": "preposition",
    "CONJ": "conjunction",
    "PRCL": "particle",
    "NUMR": "numeral",
    "NPRO": "pronoun",
}


@dataclass(frozen=True, slots=True)
class MorphAnalysis:
    """Result of morphological analysis."""
    lemma: str
    pos: str
    features: dict
    score: float = 1.0


class MorphologyEngine:
    """Engine for morphological analysis and generation."""
    
    __slots__ = ("language", "_morph")
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = pymorphy3.MorphAnalyzer() if language == "ru" and PYMORPHY_AVAILABLE else None
    
    def analyze(self, word: str) -> list[dict]:
        """Analyze a word and return possible interpretations."""
        if not self._morph:
            log.debug("analyze_fallback", word=word, reason="no_analyzer")
            return [{"lemma": word, "pos": "unknown", "features": {}}]
        
        parses = self._morph.parse(word)
        log.debug("word_analyzed", word=word, parse_count=len(parses))
        
        results = []
        for p in parses[:5]:
            features = {}
            
            # Extract case
            for case_tag, case_name in CASE_MAP.items():
                if case_tag in p.tag:
                    features["case"] = case_name
                    break
            
            # Extract number
            if "sing" in p.tag:
                features["number"] = "singular"
            elif "plur" in p.tag:
                features["number"] = "plural"
            
            # Extract gender
            for gender_tag, gender_name in GENDER_MAP.items():
                if gender_tag in p.tag:
                    features["gender"] = gender_name
                    break
            
            # Verb features
            if "perf" in p.tag:
                features["aspect"] = "perfective"
            elif "impf" in p.tag:
                features["aspect"] = "imperfective"
            
            if "pres" in p.tag:
                features["tense"] = "present"
            elif "past" in p.tag:
                features["tense"] = "past"
            elif "futr" in p.tag:
                features["tense"] = "future"
            
            for person_tag, person_name in [("1per", "1st"), ("2per", "2nd"), ("3per", "3rd")]:
                if person_tag in p.tag:
                    features["person"] = person_name
                    break
            
            pos = str(p.tag.POS) if p.tag.POS else "unknown"
            
            results.append({
                "lemma": p.normal_form,
                "pos": POS_MAP.get(pos, pos.lower()),
                "features": features,
                "score": p.score,
            })
        
        return results
    
    def analyze_result(self, word: str) -> Result[list[MorphAnalysis], AppError]:
        """Analyze with Result type for typed error handling."""
        try:
            analyses = self.analyze(word)
            return Ok([
                MorphAnalysis(
                    lemma=a["lemma"],
                    pos=a["pos"],
                    features=a["features"],
                    score=a.get("score", 1.0),
                )
                for a in analyses
            ])
        except Exception as e:
            return internal_error(
                f"Morphological analysis failed: {e}",
                origin="morphology_engine",
                cause=e,
            )
    
    def generate(
        self,
        lemma: str,
        case: str | None = None,
        number: str | None = None,
        gender: str | None = None,
        person: str | None = None,
        tense: str | None = None,
    ) -> list[dict]:
        """Generate inflected forms from a lemma."""
        if not self._morph:
            return [{"form": lemma}]
        
        parses = self._morph.parse(lemma)
        if not parses:
            return []
        
        p = parses[0]
        target_grammemes: set[str] = set()
        
        if case:
            for tag, name in CASE_MAP.items():
                if name == case:
                    target_grammemes.add(tag)
                    break
        
        if number:
            target_grammemes.add("sing" if number == "singular" else "plur")
        
        if gender:
            for tag, name in GENDER_MAP.items():
                if name == gender:
                    target_grammemes.add(tag)
                    break
        
        if person:
            person_map = {"1st": "1per", "2nd": "2per", "3rd": "3per"}
            if person in person_map:
                target_grammemes.add(person_map[person])
        
        if tense:
            tense_map = {"present": "pres", "past": "past", "future": "futr"}
            if tense in tense_map:
                target_grammemes.add(tense_map[tense])
        
        results = []
        if target_grammemes:
            inflected = p.inflect(target_grammemes)
            if inflected:
                results.append({
                    "form": inflected.word,
                    "case": case,
                    "number": number,
                    "gender": gender,
                    "person": person,
                    "tense": tense,
                })
        
        return results
    
    def get_paradigm(self, lemma: str) -> list[dict]:
        """Get complete paradigm for a lemma."""
        if not self._morph:
            return [{"form": lemma, "pos": "unknown"}]
        
        parses = self._morph.parse(lemma)
        if not parses:
            return []
        
        p = parses[0]
        pos = str(p.tag.POS) if p.tag.POS else "unknown"
        results = []
        
        if pos == "NOUN":
            for case_tag, case_name in CASE_MAP.items():
                for num_tag, num_name in NUMBER_MAP.items():
                    inflected = p.inflect({case_tag, num_tag})
                    if inflected:
                        results.append({
                            "form": inflected.word,
                            "case": case_name,
                            "number": num_name,
                            "pos": "noun",
                            "gender": GENDER_MAP.get(str(p.tag.gender)),
                        })
        
        elif pos == "VERB":
            # Present/future
            for person in ["1per", "2per", "3per"]:
                for number in ["sing", "plur"]:
                    inflected = p.inflect({person, number, "pres"})
                    if inflected:
                        results.append({
                            "form": inflected.word,
                            "person": {"1per": "1st", "2per": "2nd", "3per": "3rd"}[person],
                            "number": NUMBER_MAP[number],
                            "tense": "present",
                            "pos": "verb",
                        })
            
            # Past tense
            for gender in ["masc", "femn", "neut"]:
                inflected = p.inflect({"past", gender, "sing"})
                if inflected:
                    results.append({
                        "form": inflected.word,
                        "gender": GENDER_MAP[gender],
                        "number": "singular",
                        "tense": "past",
                        "pos": "verb",
                    })
            
            inflected = p.inflect({"past", "plur"})
            if inflected:
                results.append({
                    "form": inflected.word,
                    "number": "plural",
                    "tense": "past",
                    "pos": "verb",
                })
        
        elif pos in ["ADJF", "ADJS"]:
            for case_tag, case_name in CASE_MAP.items():
                for num_tag, num_name in NUMBER_MAP.items():
                    if num_tag == "sing":
                        for gender_tag, gender_name in GENDER_MAP.items():
                            inflected = p.inflect({case_tag, num_tag, gender_tag})
                            if inflected:
                                results.append({
                                    "form": inflected.word,
                                    "case": case_name,
                                    "number": num_name,
                                    "gender": gender_name,
                                    "pos": "adjective",
                                })
                    else:
                        inflected = p.inflect({case_tag, num_tag})
                        if inflected:
                            results.append({
                                "form": inflected.word,
                                "case": case_name,
                                "number": num_name,
                                "pos": "adjective",
                            })
        
        return results
    
    def explain_rule(self, word: str, form: str) -> dict:
        """Explain the morphological rule applied to get a form."""
        if not self._morph:
            return {"explanation": "Rule explanation not available"}
        
        analyses = self.analyze(form)
        if not analyses:
            return {"explanation": "Could not analyze form"}
        
        a = analyses[0]
        parts = []
        
        for key in ["case", "number", "gender", "tense", "person"]:
            if a["features"].get(key):
                parts.append(f"{key.capitalize()}: {a['features'][key]}")
        
        ending = form[len(a["lemma"]):] if len(form) > len(a["lemma"]) else form[-2:]
        
        return {
            "lemma": a["lemma"],
            "form": form,
            "pos": a["pos"],
            "features": a["features"],
            "ending": ending,
            "explanation": "; ".join(parts) if parts else "Base form",
        }
