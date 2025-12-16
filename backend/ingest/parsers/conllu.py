"""CoNLL-U Parser - Optimized

High-performance parser for Universal Dependencies CoNLL-U format.
Uses minimal allocations and efficient string operations.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, TextIO
import mmap
import os

# UD feature value to full name mappings (for curriculum compatibility)
_CASE_MAP = {"Nom": "nominative", "Gen": "genitive", "Dat": "dative", "Acc": "accusative",
             "Ins": "instrumental", "Loc": "prepositional", "Voc": "vocative", "Par": "partitive"}
_NUMBER_MAP = {"Sing": "singular", "Plur": "plural", "Dual": "dual"}
_GENDER_MAP = {"Masc": "masculine", "Fem": "feminine", "Neut": "neuter"}
_TENSE_MAP = {"Past": "past", "Pres": "present", "Fut": "future"}
_ASPECT_MAP = {"Imp": "imperfective", "Perf": "perfective"}
_MOOD_MAP = {"Ind": "indicative", "Imp": "imperative", "Sub": "subjunctive", "Cnd": "conditional"}


@dataclass(slots=True)
class UDToken:
    """Single token from Universal Dependencies annotation."""
    id: str
    form: str
    lemma: str
    upos: str
    xpos: str
    feats: dict[str, str]
    head: int
    deprel: str
    deps: str
    misc: dict[str, str]

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
        """Generate pattern key from morphological features.
        
        Uses full case/number/gender names to match curriculum pattern definitions.
        """
        upos = self.upos
        if upos in ("NOUN", "PROPN"):
            parts = ["noun"]
            if (c := self.case): parts.append(_CASE_MAP.get(c, c.lower()))
            if (n := self.number): parts.append(_NUMBER_MAP.get(n, n.lower()))
            if (g := self.gender): parts.append(_GENDER_MAP.get(g, g.lower()))
            return "_".join(parts)
        elif upos == "ADJ":
            parts = ["adjective"]
            if (c := self.case): parts.append(_CASE_MAP.get(c, c.lower()))
            if (g := self.gender): parts.append(_GENDER_MAP.get(g, g.lower()))
            return "_".join(parts)
        elif upos == "PRON":
            parts = ["pronoun"]
            pron_type = self.feats.get("PronType", "Prs")
            parts.append({"Prs": "personal", "Dem": "demonstrative", "Int": "interrogative",
                         "Rel": "relative", "Ind": "indefinite", "Neg": "negative",
                         "Tot": "total", "Rcp": "reciprocal", "Ref": "reflexive"}.get(pron_type, pron_type.lower()))
            if (c := self.case): parts.append(_CASE_MAP.get(c, c.lower()))
            return "_".join(parts)
        elif upos == "VERB":
            parts = ["verb"]
            if (t := self.tense): parts.append(_TENSE_MAP.get(t, t.lower()))
            if (a := self.aspect): parts.append(_ASPECT_MAP.get(a, a.lower()))
            if (m := self.mood): parts.append(_MOOD_MAP.get(m, m.lower()))
            if (p := self.person): parts.append({"1": "1st", "2": "2nd", "3": "3rd"}.get(p, p))
            if (n := self.number): parts.append(_NUMBER_MAP.get(n, n.lower()))
            if (g := self.gender): parts.append(_GENDER_MAP.get(g, g.lower()))
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
        return sum(1 for t in self.tokens if "-" not in t.id)

    @property
    def lemmas(self) -> list[str]:
        return [t.lemma for t in self.tokens if "-" not in t.id]

    def get_patterns(self) -> set[str]:
        """Extract unique pattern keys."""
        return {k for t in self.tokens if "-" not in t.id and (k := t.get_pattern_key())}

    def get_pattern_positions(self) -> list[tuple[str, int]]:
        """Get pattern keys with positions."""
        return [(k, i) for i, t in enumerate(self.tokens)
                if "-" not in t.id and (k := t.get_pattern_key())]


class CoNLLUParser:
    """High-performance CoNLL-U parser."""

    __slots__ = ()

    @staticmethod
    def _parse_features(feat_string: str) -> dict[str, str]:
        """Parse morphological features efficiently."""
        if feat_string == "_":
            return {}
        result = {}
        for pair in feat_string.split("|"):
            if (eq := pair.find("=")) != -1:
                result[pair[:eq]] = pair[eq + 1:]
        return result

    @staticmethod
    def _parse_token(parts: list[str]) -> UDToken:
        """Parse a single token from split line parts."""
        return UDToken(
            id=parts[0],
            form=parts[1],
            lemma=parts[2],
            upos=parts[3],
            xpos=parts[4],
            feats=CoNLLUParser._parse_features(parts[5]),
            head=int(parts[6]) if parts[6] != "_" else 0,
            deprel=parts[7],
            deps=parts[8],
            misc=CoNLLUParser._parse_features(parts[9]) if parts[9] != "_" else {},
        )

    def parse_file(self, path: Path | str) -> Iterator[UDSentence]:
        """Parse CoNLL-U file with optimized memory usage."""
        path = Path(path)

        with open(path, "r", encoding="utf-8") as f:
            sent_id = ""
            text = ""
            metadata: dict[str, str] = {}
            tokens: list[UDToken] = []

            for line in f:
                line = line.rstrip("\n")
                if not line:
                    if tokens:
                        yield UDSentence(sent_id=sent_id, text=text, tokens=tokens, metadata=metadata)
                        sent_id = ""
                        text = ""
                        metadata = {}
                        tokens = []
                elif line[0] == "#":
                    if line.startswith("# sent_id"):
                        sent_id = line.split("=", 1)[1].strip()
                    elif line.startswith("# text"):
                        text = line.split("=", 1)[1].strip()
                    elif "=" in line:
                        key, value = line[1:].split("=", 1)
                        metadata[key.strip()] = value.strip()
                else:
                    parts = line.split("\t")
                    if len(parts) == 10:
                        tokens.append(self._parse_token(parts))

            # Handle last sentence
            if tokens:
                yield UDSentence(sent_id=sent_id, text=text, tokens=tokens, metadata=metadata)

    def parse_stream(self, stream: TextIO) -> Iterator[UDSentence]:
        """Parse a CoNLL-U stream."""
        sent_id = ""
        text = ""
        metadata: dict[str, str] = {}
        tokens: list[UDToken] = []

        for line in stream:
            line = line.rstrip("\n")
            if not line:
                if tokens:
                    yield UDSentence(sent_id=sent_id, text=text, tokens=tokens, metadata=metadata)
                    sent_id, text, metadata, tokens = "", "", {}, []
            elif line[0] == "#":
                if line.startswith("# sent_id"):
                    sent_id = line.split("=", 1)[1].strip()
                elif line.startswith("# text"):
                    text = line.split("=", 1)[1].strip()
                elif "=" in line:
                    key, value = line[1:].split("=", 1)
                    metadata[key.strip()] = value.strip()
            else:
                parts = line.split("\t")
                if len(parts) == 10:
                    tokens.append(self._parse_token(parts))

        if tokens:
            yield UDSentence(sent_id=sent_id, text=text, tokens=tokens, metadata=metadata)

    def extract_patterns_from_file(self, path: Path | str) -> dict[str, int]:
        """Extract pattern frequencies from file."""
        counts: dict[str, int] = {}
        for sentence in self.parse_file(path):
            for pattern in sentence.get_patterns():
                counts[pattern] = counts.get(pattern, 0) + 1
        return counts
