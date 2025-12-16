"""Complexity Scoring for Sentences

Calculates difficulty scores (1-10) based on:
- Sentence length
- Pattern rarity
- Vocabulary frequency
- Grammatical complexity
"""
from dataclasses import dataclass
from collections import defaultdict
from ingest.parsers.conllu import UDSentence, UDToken


@dataclass(slots=True)
class ComplexityFactors:
    """Breakdown of complexity factors for debugging/analysis."""
    length_score: float
    pattern_rarity_score: float
    vocabulary_score: float
    case_diversity_score: float
    verb_complexity_score: float
    total: int  # Final 1-10 score


class ComplexityScorer:
    """Calculate sentence complexity scores."""

    __slots__ = (
        "pattern_frequencies",
        "lemma_frequencies",
        "top_n_lemmas",
        "_pattern_cache",
    )

    # Default frequency thresholds
    RARE_PATTERN_THRESHOLD = 0.01  # Patterns appearing in <1% of sentences
    COMMON_LEMMA_THRESHOLD = 1000  # Top N most frequent lemmas

    def __init__(
        self,
        pattern_frequencies: dict[str, float] | None = None,
        lemma_frequencies: dict[str, int] | None = None,
        top_n_lemmas: int = 1000,
    ):
        self.pattern_frequencies = pattern_frequencies or {}
        self.lemma_frequencies = lemma_frequencies or {}
        self.top_n_lemmas = top_n_lemmas
        self._pattern_cache: dict[str, float] = {}

    def get_pattern_rarity(self, pattern: str) -> float:
        """Get rarity score for a pattern (0-1, higher = rarer)."""
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]

        freq = self.pattern_frequencies.get(pattern, 0)
        if freq == 0:
            rarity = 1.0  # Unknown pattern = max rarity
        else:
            # Inverse frequency, normalized
            max_freq = max(self.pattern_frequencies.values()) if self.pattern_frequencies else 1
            rarity = 1 - (freq / max_freq)

        self._pattern_cache[pattern] = rarity
        return rarity

    def is_common_lemma(self, lemma: str) -> bool:
        """Check if lemma is in top N most common."""
        if not self.lemma_frequencies:
            return True  # Assume common if no data
        rank = self.lemma_frequencies.get(lemma, float("inf"))
        return rank <= self.top_n_lemmas

    def score_length(self, sentence: UDSentence) -> float:
        """Score based on sentence length (0-2 points)."""
        word_count = sentence.word_count
        if word_count <= 5:
            return 0
        elif word_count <= 10:
            return 0.5
        elif word_count <= 15:
            return 1.0
        elif word_count <= 20:
            return 1.5
        return 2.0

    def score_pattern_rarity(self, sentence: UDSentence) -> float:
        """Score based on pattern rarity (0-3 points)."""
        patterns = sentence.get_patterns()
        if not patterns:
            return 0

        rare_patterns = [p for p in patterns if self.get_pattern_rarity(p) > 0.8]
        return min(len(rare_patterns), 3)

    def score_vocabulary(self, sentence: UDSentence) -> float:
        """Score based on vocabulary difficulty (0-2 points)."""
        lemmas = sentence.lemmas
        if not lemmas:
            return 0

        uncommon_count = sum(1 for l in lemmas if not self.is_common_lemma(l))
        ratio = uncommon_count / len(lemmas)

        if ratio >= 0.5:
            return 2.0
        elif ratio >= 0.3:
            return 1.0
        elif ratio >= 0.1:
            return 0.5
        return 0

    def score_case_diversity(self, sentence: UDSentence) -> float:
        """Score based on case variety (0-2 points)."""
        cases = set()
        for token in sentence.tokens:
            if token.case and not token.is_multiword:
                cases.add(token.case)

        if len(cases) >= 5:
            return 2.0
        elif len(cases) >= 4:
            return 1.5
        elif len(cases) >= 3:
            return 1.0
        elif len(cases) >= 2:
            return 0.5
        return 0

    def score_verb_complexity(self, sentence: UDSentence) -> float:
        """Score based on verbal complexity (0-2 points)."""
        score = 0.0
        for token in sentence.tokens:
            if token.is_multiword:
                continue
            if token.upos == "VERB":
                # Subjunctive/conditional mood
                if token.mood in ("Sub", "Cnd"):
                    score += 1.0
                # Passive voice
                if token.voice == "Pass":
                    score += 0.5
                # Complex tenses
                if token.tense in ("Pqp", "Fut"):
                    score += 0.5

        return min(score, 2.0)

    def calculate(self, sentence: UDSentence) -> ComplexityFactors:
        """Calculate full complexity breakdown."""
        length = self.score_length(sentence)
        pattern_rarity = self.score_pattern_rarity(sentence)
        vocabulary = self.score_vocabulary(sentence)
        case_diversity = self.score_case_diversity(sentence)
        verb_complexity = self.score_verb_complexity(sentence)

        raw_total = length + pattern_rarity + vocabulary + case_diversity + verb_complexity
        # Normalize to 1-10 scale (max raw = 11, min = 0)
        normalized = int(max(1, min(10, (raw_total / 11) * 10 + 1)))

        return ComplexityFactors(
            length_score=length,
            pattern_rarity_score=pattern_rarity,
            vocabulary_score=vocabulary,
            case_diversity_score=case_diversity,
            verb_complexity_score=verb_complexity,
            total=normalized,
        )

    def score(self, sentence: UDSentence) -> int:
        """Get final complexity score (1-10)."""
        return self.calculate(sentence).total

    @classmethod
    def from_corpus(cls, sentences: list[UDSentence]) -> "ComplexityScorer":
        """Create a scorer calibrated from a corpus."""
        # Calculate pattern frequencies
        pattern_counts: dict[str, int] = defaultdict(int)
        total_sentences = len(sentences)

        for sent in sentences:
            for pattern in sent.get_patterns():
                pattern_counts[pattern] += 1

        pattern_frequencies = {
            p: count / total_sentences for p, count in pattern_counts.items()
        }

        # Calculate lemma frequencies
        lemma_counts: dict[str, int] = defaultdict(int)
        for sent in sentences:
            for lemma in sent.lemmas:
                lemma_counts[lemma] += 1

        # Rank lemmas by frequency
        sorted_lemmas = sorted(lemma_counts.items(), key=lambda x: -x[1])
        lemma_frequencies = {lemma: rank + 1 for rank, (lemma, _) in enumerate(sorted_lemmas)}

        return cls(
            pattern_frequencies=pattern_frequencies,
            lemma_frequencies=lemma_frequencies,
        )

