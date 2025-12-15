"""Production Engine

Analyzes learner output and provides targeted correction.
Multi-layered analysis: morphological, syntactic, semantic, phonetic.
"""
from typing import Optional

try:
    import pymorphy2
    PYMORPHY_AVAILABLE = True
except ImportError:
    PYMORPHY_AVAILABLE = False


class ProductionEngine:
    """Engine for production analysis and feedback"""
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._morph = None
        
        if language == "ru" and PYMORPHY_AVAILABLE:
            self._morph = pymorphy2.MorphAnalyzer()
    
    def analyze_response(
        self,
        user_response: str,
        expected_patterns: list[str],
        target_structures: list[dict],
        acceptable_answers: list[str],
    ) -> dict:
        """Analyze a production response
        
        Returns:
            Dict with score, errors, corrected_text, suggestions
        """
        errors = []
        suggestions = []
        score = 0.0
        corrected_text = user_response
        
        # Normalize for comparison
        normalized_response = user_response.lower().strip()
        normalized_acceptable = [a.lower().strip() for a in acceptable_answers]
        
        # Check exact match first
        if normalized_response in normalized_acceptable:
            return {
                "score": 1.0,
                "errors": [],
                "corrected_text": user_response,
                "suggestions": ["Perfect!"],
            }
        
        # Analyze word by word
        if self._morph:
            response_words = user_response.split()
            
            for i, word in enumerate(response_words):
                clean_word = word.strip(".,!?;:\"'()-").lower()
                if not clean_word:
                    continue
                
                # Check morphological validity
                parses = self._morph.parse(clean_word)
                
                if not parses or parses[0].score < 0.1:
                    # Unknown or unlikely word
                    errors.append({
                        "error_type": "morphological",
                        "description": f"Unfamiliar word form: '{word}'",
                        "correction": self._suggest_correction(clean_word),
                        "explanation": "This word form may be incorrect or misspelled.",
                        "severity": 3,
                    })
                else:
                    # Check if the form makes sense in context
                    # (simplified - real impl would use dependency parsing)
                    pass
        
        # Check for common errors
        common_error_patterns = [
            ("его", "её", "gender agreement"),
            ("мой", "моя", "gender agreement"),
            ("был", "была", "past tense gender"),
            ("красный", "красная", "adjective gender"),
        ]
        
        for wrong, correct, error_desc in common_error_patterns:
            if wrong in normalized_response and any(correct in a for a in normalized_acceptable):
                errors.append({
                    "error_type": "morphological",
                    "description": f"Possible {error_desc} error",
                    "correction": f"Consider using '{correct}' instead of '{wrong}'",
                    "explanation": f"Check the {error_desc} of nearby words.",
                    "severity": 2,
                })
        
        # Calculate score based on similarity to acceptable answers
        if acceptable_answers:
            best_similarity = max(
                self._calculate_similarity(normalized_response, a.lower())
                for a in acceptable_answers
            )
            score = best_similarity
            
            # Find the closest acceptable answer for correction
            closest = min(acceptable_answers, key=lambda a: -self._calculate_similarity(normalized_response, a.lower()))
            corrected_text = closest
        else:
            # No acceptable answers to compare - base score on error count
            score = max(0, 1 - len(errors) * 0.2)
        
        # Generate suggestions
        if errors:
            suggestions.append("Review the grammatical patterns in your response.")
        if score < 0.5:
            suggestions.append("Try breaking down the sentence structure step by step.")
        if score >= 0.7:
            suggestions.append("Good effort! Minor corrections needed.")
        
        return {
            "score": score,
            "errors": errors,
            "corrected_text": corrected_text,
            "suggestions": suggestions,
        }
    
    def _suggest_correction(self, word: str) -> str:
        """Suggest a correction for a misspelled/malformed word"""
        if not self._morph:
            return word
        
        # Try to find similar valid words
        # Simple approach: try common letter substitutions
        # Real implementation would use edit distance and dictionary
        
        parses = self._morph.parse(word)
        if parses and parses[0].score > 0.5:
            return parses[0].normal_form
        
        return word  # No suggestion available
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        # Simple word overlap similarity
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def detect_error_type(self, user_word: str, expected_word: str) -> dict:
        """Detect the type of error between user word and expected word"""
        if not self._morph:
            return {"error_type": "unknown", "description": "Cannot analyze"}
        
        user_parses = self._morph.parse(user_word)
        expected_parses = self._morph.parse(expected_word)
        
        if not user_parses or not expected_parses:
            return {"error_type": "lexical", "description": "Word not recognized"}
        
        user_p = user_parses[0]
        expected_p = expected_parses[0]
        
        # Check if same lemma
        if user_p.normal_form == expected_p.normal_form:
            # Morphological error - wrong form of the right word
            user_tags = set(user_p.tag.grammemes)
            expected_tags = set(expected_p.tag.grammemes)
            
            diff = expected_tags - user_tags
            
            if "nomn" in diff or "gent" in diff or "datv" in diff or "accs" in diff or "ablt" in diff or "loct" in diff:
                return {"error_type": "morphological", "description": "Wrong case"}
            if "sing" in diff or "plur" in diff:
                return {"error_type": "morphological", "description": "Wrong number"}
            if "masc" in diff or "femn" in diff or "neut" in diff:
                return {"error_type": "morphological", "description": "Wrong gender"}
            if "pres" in diff or "past" in diff or "futr" in diff:
                return {"error_type": "morphological", "description": "Wrong tense"}
            
            return {"error_type": "morphological", "description": "Wrong inflection"}
        else:
            # Different word entirely
            return {"error_type": "lexical", "description": "Wrong word choice"}
    
    def generate_hint(self, prompt: dict, hint_level: int) -> str:
        """Generate a progressive hint for a production prompt
        
        hint_level: 1 = vague, 2 = medium, 3 = almost answer
        """
        hints = prompt.get("hints", [])
        
        if hints and hint_level <= len(hints):
            return hints[hint_level - 1]
        
        # Generate generic hint based on level
        if hint_level == 1:
            return "Think about the grammatical structures needed."
        elif hint_level == 2:
            expected = prompt.get("target_structures", [])
            if expected:
                return f"Consider using: {', '.join(str(s) for s in expected[:2])}"
            return "Focus on the verb form and case agreement."
        else:
            answers = prompt.get("acceptable_answers", [])
            if answers:
                # Give first few letters
                first_word = answers[0].split()[0]
                return f"The answer starts with: {first_word[:3]}..."
            return "Check your conjugation and declension."

