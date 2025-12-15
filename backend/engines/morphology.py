"""Morphological Pattern Recognition Engine

Uses pymorphy3 for Russian morphological analysis and generation.
Provides rule-based explanations for learners.
"""
from typing import Optional

from core.logging import engine_logger

log = engine_logger()

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
    log.debug("pymorphy3_loaded", available=True)
except ImportError:
    PYMORPHY_AVAILABLE = False
    log.warning("pymorphy3_unavailable", message="Morphological analysis will be limited")


# Russian case mapping
CASE_MAP = {
    "nomn": "nominative",
    "gent": "genitive", 
    "datv": "dative",
    "accs": "accusative",
    "ablt": "instrumental",
    "loct": "prepositional",
}

NUMBER_MAP = {
    "sing": "singular",
    "plur": "plural",
}

GENDER_MAP = {
    "masc": "masculine",
    "femn": "feminine",
    "neut": "neuter",
}

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


class MorphologyEngine:
    """Engine for morphological analysis and generation"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = None
        
        if language == "ru" and PYMORPHY_AVAILABLE:
            self._morph = pymorphy3.MorphAnalyzer()
    
    def analyze(self, word: str) -> list[dict]:
        """Analyze a word and return possible interpretations"""
        if not self._morph:
            log.debug("analyze_fallback", word=word, reason="no_analyzer")
            return [{"lemma": word, "pos": "unknown", "features": {}}]
        
        parses = self._morph.parse(word)
        log.debug("word_analyzed", word=word, parse_count=len(parses))
        results = []
        
        for p in parses[:5]:  # Limit to top 5 interpretations
            features = {}
            
            # Extract grammatical features
            if "nomn" in p.tag or "gent" in p.tag or "datv" in p.tag or "accs" in p.tag or "ablt" in p.tag or "loct" in p.tag:
                for case_tag, case_name in CASE_MAP.items():
                    if case_tag in p.tag:
                        features["case"] = case_name
                        break
            
            if "sing" in p.tag:
                features["number"] = "singular"
            elif "plur" in p.tag:
                features["number"] = "plural"
            
            if "masc" in p.tag:
                features["gender"] = "masculine"
            elif "femn" in p.tag:
                features["gender"] = "feminine"
            elif "neut" in p.tag:
                features["gender"] = "neuter"
            
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
            
            if "1per" in p.tag:
                features["person"] = "1st"
            elif "2per" in p.tag:
                features["person"] = "2nd"
            elif "3per" in p.tag:
                features["person"] = "3rd"
            
            pos = str(p.tag.POS) if p.tag.POS else "unknown"
            
            results.append({
                "lemma": p.normal_form,
                "pos": POS_MAP.get(pos, pos.lower()),
                "features": features,
                "score": p.score,
            })
        
        return results
    
    def generate(
        self,
        lemma: str,
        case: Optional[str] = None,
        number: Optional[str] = None,
        gender: Optional[str] = None,
        person: Optional[str] = None,
        tense: Optional[str] = None,
    ) -> list[dict]:
        """Generate inflected forms from a lemma"""
        if not self._morph:
            return [{"form": lemma}]
        
        parses = self._morph.parse(lemma)
        if not parses:
            return []
        
        # Use highest-scored parse
        p = parses[0]
        results = []
        
        # Build target tag
        target_grammemes = set()
        
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
        
        # Try to inflect
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
        """Get complete paradigm for a lemma"""
        if not self._morph:
            return [{"form": lemma, "pos": "unknown"}]
        
        parses = self._morph.parse(lemma)
        if not parses:
            return []
        
        p = parses[0]
        pos = str(p.tag.POS) if p.tag.POS else "unknown"
        results = []
        
        if pos == "NOUN":
            # Generate all noun forms
            for case_tag, case_name in CASE_MAP.items():
                for num_tag, num_name in NUMBER_MAP.items():
                    inflected = p.inflect({case_tag, num_tag})
                    if inflected:
                        results.append({
                            "form": inflected.word,
                            "case": case_name,
                            "number": num_name,
                            "pos": "noun",
                            "gender": GENDER_MAP.get(str(p.tag.gender), None),
                        })
        
        elif pos == "VERB":
            # Generate verb forms
            # Present/future tense
            for person in ["1per", "2per", "3per"]:
                for number in ["sing", "plur"]:
                    inflected = p.inflect({person, number, "pres"})
                    if inflected:
                        person_name = {"1per": "1st", "2per": "2nd", "3per": "3rd"}[person]
                        results.append({
                            "form": inflected.word,
                            "person": person_name,
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
            
            # Plural past
            inflected = p.inflect({"past", "plur"})
            if inflected:
                results.append({
                    "form": inflected.word,
                    "number": "plural",
                    "tense": "past",
                    "pos": "verb",
                })
        
        elif pos in ["ADJF", "ADJS"]:
            # Adjective forms
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
        """Explain the morphological rule applied to get a form"""
        if not self._morph:
            return {"explanation": "Rule explanation not available"}
        
        # Analyze the form
        analyses = self.analyze(form)
        if not analyses:
            return {"explanation": "Could not analyze form"}
        
        a = analyses[0]
        
        # Build explanation based on features
        parts = []
        if a["features"].get("case"):
            parts.append(f"Case: {a['features']['case']}")
        if a["features"].get("number"):
            parts.append(f"Number: {a['features']['number']}")
        if a["features"].get("gender"):
            parts.append(f"Gender: {a['features']['gender']}")
        if a["features"].get("tense"):
            parts.append(f"Tense: {a['features']['tense']}")
        if a["features"].get("person"):
            parts.append(f"Person: {a['features']['person']}")
        
        # Determine ending
        if len(form) > len(a["lemma"]):
            ending = form[len(a["lemma"]):]
        else:
            ending = form[-2:] if len(form) >= 2 else form
        
        return {
            "lemma": a["lemma"],
            "form": form,
            "pos": a["pos"],
            "features": a["features"],
            "ending": ending,
            "explanation": "; ".join(parts) if parts else "Base form",
        }

