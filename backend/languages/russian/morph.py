"""Russian Morphological Pattern Recognition Engine

Uses pymorphy3 for Russian morphological analysis and generation.
Provides rule-based explanations with monadic error handling.
Includes pattern extraction for teaching inflections as generative rules.
"""
from dataclasses import dataclass, field
import random

from core.logging import engine_logger
from core.errors import AppError, Ok, Result, internal_error
from .maps import CASE_MAP, CASE_MAP_REV, NUMBER_MAP, NUMBER_MAP_REV, GENDER_MAP, POS_MAP
from .declension import DECLENSION_PATTERNS, ENDING_DISTRACTORS

log = engine_logger()

try:
    import pymorphy3
    PYMORPHY_AVAILABLE = True
    log.debug("pymorphy3_loaded", available=True)
except ImportError:
    PYMORPHY_AVAILABLE = False
    log.warning("pymorphy3_unavailable", message="Morphological analysis will be limited")


@dataclass(frozen=True, slots=True)
class MorphAnalysis:
    """Result of morphological analysis."""
    lemma: str
    pos: str
    features: dict
    score: float = 1.0


@dataclass(slots=True)
class StemEnding:
    """Word decomposed into stem and ending."""
    word: str
    stem: str
    ending: str
    lemma: str
    gender: str | None = None
    case: str | None = None
    number: str | None = None
    pattern_id: str | None = None


@dataclass(slots=True)
class PatternParadigm:
    """Complete paradigm for pattern-based teaching."""
    lemma: str
    translation: str
    gender: str
    pattern_id: str
    pattern_name: str
    stem: str
    cells: list[dict] = field(default_factory=list)


class RussianMorphologyEngine:
    """Engine for Russian morphological analysis and generation."""

    __slots__ = ("_morph",)

    def __init__(self):
        self._morph = pymorphy3.MorphAnalyzer() if PYMORPHY_AVAILABLE else None

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
                MorphAnalysis(lemma=a["lemma"], pos=a["pos"], features=a["features"], score=a.get("score", 1.0))
                for a in analyses
            ])
        except Exception as e:
            return internal_error(f"Morphological analysis failed: {e}", origin="morphology_engine", cause=e)

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
            tag = CASE_MAP_REV.get(case)
            if tag:
                target_grammemes.add(tag)

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
                results.append({"form": inflected.word, "number": "plural", "tense": "past", "pos": "verb"})

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
        parts = [f"{k.capitalize()}: {a['features'][k]}" for k in ["case", "number", "gender", "tense", "person"] if a["features"].get(k)]
        ending = form[len(a["lemma"]):] if len(form) > len(a["lemma"]) else form[-2:]

        return {
            "lemma": a["lemma"],
            "form": form,
            "pos": a["pos"],
            "features": a["features"],
            "ending": ending,
            "explanation": "; ".join(parts) if parts else "Base form",
        }

    # === Pattern Extraction Methods for Teaching ===

    def extract_stem_ending(self, word: str) -> StemEnding:
        """Extract stem and ending from a word for pattern visualization."""
        if not self._morph:
            return StemEnding(word=word, stem=word, ending="", lemma=word)

        parses = self._morph.parse(word)
        if not parses:
            return StemEnding(word=word, stem=word, ending="", lemma=word)

        p = parses[0]
        lemma = p.normal_form

        gender = case = number = None
        for g_tag, g_name in GENDER_MAP.items():
            if g_tag in p.tag:
                gender = g_name
                break
        for c_tag, c_name in CASE_MAP.items():
            if c_tag in p.tag:
                case = c_name
                break
        number = "singular" if "sing" in p.tag else "plural" if "plur" in p.tag else None

        stem, ending = self._compute_stem_ending(word, lemma, gender)
        pattern_id = self._identify_pattern(lemma, gender)

        return StemEnding(word=word, stem=stem, ending=ending, lemma=lemma, gender=gender, case=case, number=number, pattern_id=pattern_id)

    def _compute_stem_ending(self, word: str, lemma: str, gender: str | None) -> tuple[str, str]:
        """Compute stem and ending using lemma comparison."""
        word_lower, lemma_lower = word.lower(), lemma.lower()
        min_len = min(len(word_lower), len(lemma_lower))
        stem_len = 0

        for i in range(min_len):
            if word_lower[i] == lemma_lower[i]:
                stem_len = i + 1
            else:
                break

        if gender == "feminine" and lemma_lower.endswith(("а", "я")):
            stem_len = min(stem_len, len(lemma_lower) - 1)
        elif gender == "neuter" and lemma_lower.endswith(("о", "е")):
            stem_len = min(stem_len, len(lemma_lower) - 1)
        elif gender == "masculine" and not lemma_lower.endswith(("ь", "й")):
            stem_len = len(lemma_lower)

        stem = word[:stem_len] if stem_len > 0 else word[:-1] if len(word) > 1 else word
        ending = word[stem_len:] if stem_len < len(word) else ""
        return stem, ending

    def _identify_pattern(self, lemma: str, gender: str | None) -> str | None:
        """Identify which declension pattern a noun follows."""
        lemma_lower = lemma.lower()

        if gender == "feminine" and lemma_lower.endswith(("а", "я")):
            return "fem_a_declension"
        elif gender == "masculine" and not lemma_lower.endswith(("а", "я", "ь")):
            return "masc_hard_declension"
        elif gender == "neuter" and lemma_lower.endswith(("о", "е")):
            return "neut_o_declension"
        return None

    def get_pattern_paradigm(self, lemma: str, translation: str = "") -> PatternParadigm:
        """Get paradigm with pattern info for teaching."""
        if not self._morph:
            return PatternParadigm(lemma=lemma, translation=translation, gender="unknown", pattern_id="unknown", pattern_name="Unknown", stem=lemma, cells=[])

        parses = self._morph.parse(lemma)
        if not parses:
            return PatternParadigm(lemma=lemma, translation=translation, gender="unknown", pattern_id="unknown", pattern_name="Unknown", stem=lemma, cells=[])

        p = parses[0]
        gender = None
        for g_tag, g_name in GENDER_MAP.items():
            if g_tag in p.tag:
                gender = g_name
                break

        pattern_id = self._identify_pattern(lemma, gender) or "unknown"
        pattern_name = DECLENSION_PATTERNS.get(pattern_id.replace("_declension", ""), {}).get("name", "Unknown")
        stem, _ = self._compute_stem_ending(lemma, lemma, gender)

        cells = []
        for case_tag, case_name in CASE_MAP.items():
            for num_tag, num_name in NUMBER_MAP.items():
                inflected = p.inflect({case_tag, num_tag})
                if inflected:
                    form = inflected.word
                    _, ending = self._compute_stem_ending(form, lemma, gender)
                    cells.append({"case": case_name, "number": num_name, "form": form, "stem": stem, "ending": ending})

        return PatternParadigm(lemma=lemma, translation=translation, gender=gender or "unknown", pattern_id=pattern_id, pattern_name=pattern_name, stem=stem, cells=cells)

    def get_ending_options(self, case: str, correct_ending: str, count: int = 4) -> list[str]:
        """Get distractor endings for pattern exercises."""
        distractors = ENDING_DISTRACTORS.get(case, ["а", "о", "е", "ы"])
        options = [correct_ending]

        for d in distractors:
            if d != correct_ending and len(options) < count:
                options.append(d)

        random.shuffle(options)
        return options

    def generate_form(self, lemma: str, case: str, number: str = "singular") -> str | None:
        """Generate a specific inflected form."""
        if not self._morph:
            return None

        parses = self._morph.parse(lemma)
        if not parses:
            return None

        case_tag = CASE_MAP_REV.get(case)
        num_tag = NUMBER_MAP_REV.get(number)

        if not case_tag or not num_tag:
            return None

        inflected = parses[0].inflect({case_tag, num_tag})
        return inflected.word if inflected else None


# Backward compatibility wrapper that accepts language parameter
class MorphologyEngine(RussianMorphologyEngine):
    """Backward-compatible wrapper that accepts language parameter."""
    def __init__(self, language: str = "ru"):
        # Only Russian is supported via this engine
        if language != "ru":
            raise ValueError(f"MorphologyEngine only supports 'ru', got '{language}'")
        super().__init__()
