"""CoNLL-U Parser for Universal Dependencies

Parses CoNLL-U format files from Universal Dependencies project.
Extracts sentences, tokens, morphological features, and dependency relations.

CoNLL-U Format Reference:
https://universaldependencies.org/format.html
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, TextIO
import re


@dataclass(slots=True)
class UDToken:
    """Single token from Universal Dependencies annotation."""
    id: str  # Token ID (1, 2, 3, or 1-2 for multiword)
    form: str  # Word form (surface)
    lemma: str  # Lemma (dictionary form)
    upos: str  # Universal POS tag
    xpos: str  # Language-specific POS tag
    feats: dict[str, str]  # Morphological features
    head: int  # Head token ID
    deprel: str  # Dependency relation
    deps: str  # Enhanced dependencies
    misc: dict[str, str]  # Miscellaneous annotations

    @property
    def is_multiword(self) -> bool:
        return "-" in self.id

    @property
    def case(self) -> str | None:
        return self.feats.get("Case")

    @property
    def number(self) -> str | None:
        return self.feats.get("Number")

    @property
    def gender(self) -> str | None:
        return self.feats.get("Gender")

    @property
    def tense(self) -> str | None:
        return self.feats.get("Tense")

    @property
    def person(self) -> str | None:
        return self.feats.get("Person")

    @property
    def aspect(self) -> str | None:
        return self.feats.get("Aspect")

    @property
    def mood(self) -> str | None:
        return self.feats.get("Mood")

    @property
    def voice(self) -> str | None:
        return self.feats.get("Voice")

    def get_pattern_key(self) -> str | None:
        """Generate a pattern key from morphological features for grouping."""
        if self.upos in ("NOUN", "PROPN", "ADJ", "DET", "PRON", "NUM"):
            parts = [self.upos.lower()]
            if self.case:
                parts.append(self.case.lower())
            if self.number:
                parts.append(self.number.lower())
            if self.gender:
                parts.append(self.gender.lower())
            return "_".join(parts)
        elif self.upos == "VERB":
            parts = ["verb"]
            if self.tense:
                parts.append(self.tense.lower())
            if self.aspect:
                parts.append(self.aspect.lower())
            if self.mood:
                parts.append(self.mood.lower())
            if self.person:
                parts.append(f"p{self.person}")
            if self.number:
                parts.append(self.number.lower())
            return "_".join(parts)
        return None


@dataclass(slots=True)
class UDSentence:
    """Parsed sentence from Universal Dependencies."""
    sent_id: str
    text: str
    tokens: list[UDToken] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len([t for t in self.tokens if not t.is_multiword])

    @property
    def lemmas(self) -> list[str]:
        return [t.lemma for t in self.tokens if not t.is_multiword]

    def get_patterns(self) -> set[str]:
        """Extract unique pattern keys from all tokens."""
        patterns = set()
        for token in self.tokens:
            if not token.is_multiword:
                key = token.get_pattern_key()
                if key:
                    patterns.add(key)
        return patterns

    def get_pattern_positions(self) -> list[tuple[str, int]]:
        """Get pattern keys with their positions in the sentence."""
        result = []
        for i, token in enumerate(self.tokens):
            if not token.is_multiword:
                key = token.get_pattern_key()
                if key:
                    result.append((key, i))
        return result


class CoNLLUParser:
    """Parser for CoNLL-U format files."""

    __slots__ = ("_feat_pattern", "_misc_pattern")

    def __init__(self):
        self._feat_pattern = re.compile(r"([^=|]+)=([^=|]+)")
        self._misc_pattern = re.compile(r"([^=|]+)=([^=|]+)")

    def parse_features(self, feat_string: str) -> dict[str, str]:
        """Parse morphological features from CoNLL-U format."""
        if feat_string == "_":
            return {}
        return dict(self._feat_pattern.findall(feat_string))

    def parse_misc(self, misc_string: str) -> dict[str, str]:
        """Parse miscellaneous column from CoNLL-U format."""
        if misc_string == "_":
            return {}
        return dict(self._misc_pattern.findall(misc_string))

    def parse_token(self, line: str) -> UDToken:
        """Parse a single token line."""
        parts = line.split("\t")
        if len(parts) != 10:
            raise ValueError(f"Invalid CoNLL-U token line: expected 10 fields, got {len(parts)}")

        return UDToken(
            id=parts[0],
            form=parts[1],
            lemma=parts[2],
            upos=parts[3],
            xpos=parts[4],
            feats=self.parse_features(parts[5]),
            head=int(parts[6]) if parts[6] != "_" else 0,
            deprel=parts[7],
            deps=parts[8],
            misc=self.parse_misc(parts[9]),
        )

    def parse_sentence(self, lines: list[str]) -> UDSentence:
        """Parse a sentence block (metadata + tokens)."""
        sent_id = ""
        text = ""
        metadata: dict[str, str] = {}
        tokens: list[UDToken] = []

        for line in lines:
            if line.startswith("# sent_id"):
                sent_id = line.split("=", 1)[1].strip()
            elif line.startswith("# text"):
                text = line.split("=", 1)[1].strip()
            elif line.startswith("#"):
                # Other metadata
                if "=" in line:
                    key, value = line[1:].split("=", 1)
                    metadata[key.strip()] = value.strip()
            elif line and not line.startswith("#"):
                tokens.append(self.parse_token(line))

        return UDSentence(sent_id=sent_id, text=text, tokens=tokens, metadata=metadata)

    def parse_file(self, path: Path | str) -> Iterator[UDSentence]:
        """Parse a CoNLL-U file and yield sentences."""
        with open(path, "r", encoding="utf-8") as f:
            yield from self.parse_stream(f)

    def parse_stream(self, stream: TextIO) -> Iterator[UDSentence]:
        """Parse a CoNLL-U stream and yield sentences."""
        current_block: list[str] = []

        for line in stream:
            line = line.rstrip("\n")
            if not line:
                if current_block:
                    yield self.parse_sentence(current_block)
                    current_block = []
            else:
                current_block.append(line)

        # Handle last sentence if file doesn't end with blank line
        if current_block:
            yield self.parse_sentence(current_block)

    def parse_string(self, content: str) -> Iterator[UDSentence]:
        """Parse a CoNLL-U string and yield sentences."""
        from io import StringIO
        yield from self.parse_stream(StringIO(content))

    def extract_patterns_from_file(self, path: Path | str) -> dict[str, int]:
        """Extract all unique patterns and their frequencies from a file."""
        pattern_counts: dict[str, int] = {}
        for sentence in self.parse_file(path):
            for pattern in sentence.get_patterns():
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        return pattern_counts

