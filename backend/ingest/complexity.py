"""Complexity Scoring for Sentences

Calculates difficulty scores (1-10) based on:
- Sentence length
- Pattern rarity
- Vocabulary frequency
- Grammatical complexity
"""
from dataclasses import dataclass
from collections import defaultdict
from ingest.parsers.conllu import UDSentence


@dataclass(slots=True)
class ComplexityFactors:
    """Breakdown of complexity factors for debugging/analysis."""
    length_score: float
    pattern_rarity_score: float
    vocabulary_score: float
    case_diversity_score: float
    verb_complexity_score: float
    total: int


class ComplexityScorer:
    """Calculate sentence complexity scores."""

    __slots__ = ("pattern_frequencies", "lemma_frequencies", "top_n_lemmas", "_max_freq")

    RARE_PATTERN_THRESHOLD = 0.01
    COMMON_LEMMA_THRESHOLD = 1000

    def __init__(
        self,
        pattern_frequencies: dict[str, float] | None = None,
        lemma_frequencies: dict[str, int] | None = None,
        top_n_lemmas: int = 1000,
    ):
        self.pattern_frequencies = pattern_frequencies or {}
        self.lemma_frequencies = lemma_frequencies or {}
        self.top_n_lemmas = top_n_lemmas
        self._max_freq = max(self.pattern_frequencies.values()) if self.pattern_frequencies else 1.0

    def get_pattern_rarity(self, pattern: str) -> float:
        """Get rarity score for a pattern (0-1, higher = rarer)."""
        return 1.0 if (f := self.pattern_frequencies.get(pattern)) is None else 1 - (f / self._max_freq)

    def is_common_lemma(self, lemma: str) -> bool:
        """Check if lemma is in top N most common."""
        return not self.lemma_frequencies or self.lemma_frequencies.get(lemma, float("inf")) <= self.top_n_lemmas

    def score_length(self, sentence: UDSentence) -> float:
        """Score based on sentence length (0-2 points)."""
        wc = sentence.word_count
        return 0 if wc <= 5 else 0.5 if wc <= 10 else 1.0 if wc <= 15 else 1.5 if wc <= 20 else 2.0

    def score_pattern_rarity(self, sentence: UDSentence) -> float:
        """Score based on pattern rarity (0-3 points)."""
        return min(sum(1 for p in sentence.get_patterns() if self.get_pattern_rarity(p) > 0.8), 3)

    def score_vocabulary(self, sentence: UDSentence) -> float:
        """Score based on vocabulary difficulty (0-2 points)."""
        lemmas = sentence.lemmas
        if not lemmas:
            return 0
        ratio = sum(1 for l in lemmas if not self.is_common_lemma(l)) / len(lemmas)
        return 2.0 if ratio >= 0.5 else 1.0 if ratio >= 0.3 else 0.5 if ratio >= 0.1 else 0

    def score_case_diversity(self, sentence: UDSentence) -> float:
        """Score based on case variety (0-2 points)."""
        n = len({t.feats.get("Case") for t in sentence.tokens if "-" not in t.id and t.feats.get("Case")})
        return 2.0 if n >= 5 else 1.5 if n >= 4 else 1.0 if n >= 3 else 0.5 if n >= 2 else 0

    def score_verb_complexity(self, sentence: UDSentence) -> float:
        """Score based on verbal complexity (0-2 points)."""
        s = 0.0
        for t in sentence.tokens:
            if "-" in t.id or t.upos != "VERB":
                continue
            if t.feats.get("Mood") in ("Sub", "Cnd"):
                s += 1.0
            if t.feats.get("Voice") == "Pass":
                s += 0.5
            if t.feats.get("Tense") in ("Pqp", "Fut"):
                s += 0.5
        return min(s, 2.0)

    def calculate(self, sentence: UDSentence) -> ComplexityFactors:
        """Calculate full complexity breakdown."""
        length = self.score_length(sentence)
        rarity = self.score_pattern_rarity(sentence)
        vocab = self.score_vocabulary(sentence)
        cases = self.score_case_diversity(sentence)
        verbs = self.score_verb_complexity(sentence)
        raw = length + rarity + vocab + cases + verbs
        return ComplexityFactors(
            length_score=length,
            pattern_rarity_score=rarity,
            vocabulary_score=vocab,
            case_diversity_score=cases,
            verb_complexity_score=verbs,
            total=max(1, min(10, int(raw / 11 * 10 + 1))),
        )

    def score(self, sentence: UDSentence) -> int:
        """Get final complexity score (1-10)."""
        return self.calculate(sentence).total

    @classmethod
    def from_corpus(cls, sentences: list[UDSentence]) -> "ComplexityScorer":
        """Create a scorer calibrated from a corpus."""
        total = len(sentences)
        pattern_counts: dict[str, int] = defaultdict(int)
        lemma_counts: dict[str, int] = defaultdict(int)

        for s in sentences:
            for p in s.get_patterns():
                pattern_counts[p] += 1
            for l in s.lemmas:
                lemma_counts[l] += 1

        return cls(
            pattern_frequencies={p: c / total for p, c in pattern_counts.items()},
            lemma_frequencies={l: r + 1 for r, (l, _) in enumerate(sorted(lemma_counts.items(), key=lambda x: -x[1]))},
        )
