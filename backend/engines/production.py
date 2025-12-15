"""Production Engine with Result Types

Analyzes learner output and provides targeted correction.
Multi-layered analysis with monadic error handling.
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


@dataclass(frozen=True, slots=True)
class ProductionError:
    """Structured production error."""
    error_type: str
    description: str
    correction: str
    explanation: str
    severity: int


@dataclass(frozen=True, slots=True)
class ProductionAnalysis:
    """Result of production analysis."""
    score: float
    errors: list[ProductionError]
    corrected_text: str
    suggestions: list[str]


class ProductionEngine:
    """Engine for production analysis and feedback."""
    
    __slots__ = ("language", "_morph")
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = pymorphy2.MorphAnalyzer() if language == "ru" and PYMORPHY_AVAILABLE else None
    
    def analyze_response(
        self,
        user_response: str,
        expected_patterns: list[str],
        target_structures: list[dict],
        acceptable_answers: list[str],
    ) -> dict:
        """Analyze a production response."""
        errors: list[dict] = []
        suggestions: list[str] = []
        corrected_text = user_response
        
        normalized_response = user_response.lower().strip()
        normalized_acceptable = [a.lower().strip() for a in acceptable_answers]
        
        # Exact match
        if normalized_response in normalized_acceptable:
            return {"score": 1.0, "errors": [], "corrected_text": user_response, "suggestions": ["Perfect!"]}
        
        # Word-by-word analysis
        if self._morph:
            for word in user_response.split():
                clean = word.strip(".,!?;:\"'()-").lower()
                if not clean:
                    continue
                
                parses = self._morph.parse(clean)
                if not parses or parses[0].score < 0.1:
                    errors.append({
                        "error_type": "morphological",
                        "description": f"Unfamiliar word form: '{word}'",
                        "correction": self._suggest_correction(clean),
                        "explanation": "This word form may be incorrect or misspelled.",
                        "severity": 3,
                    })
        
        # Check common errors
        for wrong, correct, desc in [
            ("его", "её", "gender agreement"),
            ("мой", "моя", "gender agreement"),
            ("был", "была", "past tense gender"),
        ]:
            if wrong in normalized_response and any(correct in a for a in normalized_acceptable):
                errors.append({
                    "error_type": "morphological",
                    "description": f"Possible {desc} error",
                    "correction": f"Consider '{correct}' instead of '{wrong}'",
                    "explanation": f"Check {desc} of nearby words.",
                    "severity": 2,
                })
        
        # Calculate score
        if acceptable_answers:
            score = max(self._similarity(normalized_response, a.lower()) for a in acceptable_answers)
            corrected_text = min(acceptable_answers, key=lambda a: -self._similarity(normalized_response, a.lower()))
        else:
            score = max(0, 1 - len(errors) * 0.2)
        
        # Suggestions
        if errors:
            suggestions.append("Review the grammatical patterns in your response.")
        if score < 0.5:
            suggestions.append("Try breaking down the sentence structure step by step.")
        elif score >= 0.7:
            suggestions.append("Good effort! Minor corrections needed.")
        
        return {"score": score, "errors": errors, "corrected_text": corrected_text, "suggestions": suggestions}
    
    def analyze_response_result(
        self,
        user_response: str,
        expected_patterns: list[str],
        target_structures: list[dict],
        acceptable_answers: list[str],
    ) -> Result[ProductionAnalysis, AppError]:
        """Analyze with Result type."""
        try:
            result = self.analyze_response(user_response, expected_patterns, target_structures, acceptable_answers)
            return Ok(ProductionAnalysis(
                score=result["score"],
                errors=[ProductionError(**e) for e in result["errors"]],
                corrected_text=result["corrected_text"],
                suggestions=result["suggestions"],
            ))
        except Exception as e:
            return internal_error(f"Production analysis failed: {e}", origin="production_engine", cause=e)
    
    def _suggest_correction(self, word: str) -> str:
        if not self._morph:
            return word
        parses = self._morph.parse(word)
        return parses[0].normal_form if parses and parses[0].score > 0.5 else word
    
    def _similarity(self, s1: str, s2: str) -> float:
        words1, words2 = set(s1.split()), set(s2.split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)
    
    def detect_error_type(self, user_word: str, expected_word: str) -> dict:
        """Detect error type between user and expected word."""
        if not self._morph:
            return {"error_type": "unknown", "description": "Cannot analyze"}
        
        user_p = self._morph.parse(user_word)
        expected_p = self._morph.parse(expected_word)
        
        if not user_p or not expected_p:
            return {"error_type": "lexical", "description": "Word not recognized"}
        
        if user_p[0].normal_form == expected_p[0].normal_form:
            diff = set(expected_p[0].tag.grammemes) - set(user_p[0].tag.grammemes)
            
            if any(c in diff for c in ("nomn", "gent", "datv", "accs", "ablt", "loct")):
                return {"error_type": "morphological", "description": "Wrong case"}
            if "sing" in diff or "plur" in diff:
                return {"error_type": "morphological", "description": "Wrong number"}
            if any(g in diff for g in ("masc", "femn", "neut")):
                return {"error_type": "morphological", "description": "Wrong gender"}
            if any(t in diff for t in ("pres", "past", "futr")):
                return {"error_type": "morphological", "description": "Wrong tense"}
            return {"error_type": "morphological", "description": "Wrong inflection"}
        
        return {"error_type": "lexical", "description": "Wrong word choice"}
    
    def generate_hint(self, prompt: dict, hint_level: int) -> str:
        """Generate progressive hint for production prompt."""
        hints = prompt.get("hints", [])
        if hints and hint_level <= len(hints):
            return hints[hint_level - 1]
        
        if hint_level == 1:
            return "Think about the grammatical structures needed."
        if hint_level == 2:
            structures = prompt.get("target_structures", [])
            return f"Consider using: {', '.join(str(s) for s in structures[:2])}" if structures else "Focus on verb form and case."
        
        answers = prompt.get("acceptable_answers", [])
        if answers:
            return f"Starts with: {answers[0].split()[0][:3]}..."
        return "Check your conjugation and declension."
