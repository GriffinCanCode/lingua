"""Wiktionary Dump Parser

Parses Wiktionary XML dumps to extract:
- Lemmas with POS tags
- Full declension/conjugation paradigms
- Etymology information
- Definitions and translations

Russian Wiktionary structure is parsed for morphological data.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element


@dataclass(slots=True)
class InflectionForm:
    """Single inflected form with its features."""
    form: str
    case: str | None = None
    number: str | None = None
    gender: str | None = None
    person: str | None = None
    tense: str | None = None
    mood: str | None = None
    aspect: str | None = None


@dataclass(slots=True)
class EtymologyInfo:
    """Etymology information for a word."""
    origin_language: str | None = None
    origin_word: str | None = None
    relation_type: str = "derived_from"
    notes: str | None = None


@dataclass(slots=True)
class WiktionaryEntry:
    """Parsed Wiktionary entry for a word."""
    title: str
    language: str
    pos: str
    gender: str | None = None
    aspect: str | None = None
    definitions: list[str] = field(default_factory=list)
    inflections: list[InflectionForm] = field(default_factory=list)
    etymology: EtymologyInfo | None = None
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    translations: dict[str, list[str]] = field(default_factory=dict)
    pronunciation: str | None = None
    stress: str | None = None
    declension_class: str | None = None
    conjugation_class: str | None = None
    extra_data: dict = field(default_factory=dict)


# Pre-compiled patterns
_NS_RE = re.compile(r"\{[^}]+\}")
_SECTION_RE = re.compile(r"^(={2,})\s*(.+?)\s*\1", re.MULTILINE)
_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")
_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_MARKUP_RE = re.compile(r"[']{2,}|<[^>]+>")
_ETYM_RE = re.compile(r"\{\{этимология\|([^}]+)\}\}")
_FROM_RE = re.compile(r"от\s+\[\[([^\]]+)\]\]")
_IPA_RE = re.compile(r"\{\{IPA\|([^}]+)\}\}")

# Lookup maps
_CASE_MAP = {
    "им": "nominative", "именительный": "nominative", "nom": "nominative",
    "рд": "genitive", "родительный": "genitive", "gen": "genitive",
    "дт": "dative", "дательный": "dative", "dat": "dative",
    "вн": "accusative", "винительный": "accusative", "acc": "accusative",
    "тв": "instrumental", "творительный": "instrumental", "ins": "instrumental",
    "пр": "prepositional", "предложный": "prepositional", "prep": "prepositional", "loc": "prepositional",
}
_NUMBER_MAP = {
    "ед": "singular", "единственное": "singular", "sg": "singular",
    "мн": "plural", "множественное": "plural", "pl": "plural",
}
_GENDER_MAP = {
    "м": "masculine", "мужской": "masculine", "m": "masculine",
    "ж": "feminine", "женский": "feminine", "f": "feminine",
    "с": "neuter", "средний": "neuter", "n": "neuter",
}
_POS_MAP = {
    "существительное": "noun", "noun": "noun",
    "глагол": "verb", "verb": "verb",
    "прилагательное": "adjective", "adjective": "adjective", "adj": "adjective",
    "наречие": "adverb", "adverb": "adverb", "adv": "adverb",
    "местоимение": "pronoun", "pronoun": "pronoun",
    "предлог": "preposition", "preposition": "preposition",
    "союз": "conjunction", "conjunction": "conjunction",
    "частица": "particle", "particle": "particle",
    "числительное": "numeral", "numeral": "numeral",
}
_LANG_SECTIONS = frozenset({"Russian", "Русский", "ru"})


class WiktionaryParser:
    """Parser for Wiktionary XML dumps."""

    __slots__ = ()

    @staticmethod
    def _clean_form(text: str) -> str:
        """Clean a word form from wiki markup."""
        return _MARKUP_RE.sub("", _LINK_RE.sub(r"\1", text)).strip()

    @staticmethod
    def _parse_inflection_table(parts: list[str], is_verb: bool) -> list[InflectionForm]:
        """Parse declension/conjugation from template parts."""
        forms = []
        if is_verb:
            persons, numbers = ["1st", "2nd", "3rd"], ["singular", "plural"]
            idx = 1
            for num in numbers:
                for pers in persons:
                    if idx < len(parts) and (f := parts[idx].strip()) and f != "-":
                        forms.append(InflectionForm(
                            form=WiktionaryParser._clean_form(f),
                            person=pers, number=num, tense="present"
                        ))
                    idx += 1
        else:
            cases = ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"]
            numbers = ["singular", "plural"]
            idx = 1
            for num in numbers:
                for case in cases:
                    if idx < len(parts) and (f := parts[idx].strip()) and f != "-":
                        forms.append(InflectionForm(
                            form=WiktionaryParser._clean_form(f), case=case, number=num
                        ))
                    idx += 1
        return forms

    @staticmethod
    def _extract_definitions(text: str) -> list[str]:
        """Extract definitions from wiki text."""
        return [
            WiktionaryParser._clean_form(line[2:])
            for line in text.split("\n")
            if line.startswith("# ") and not line.startswith("# *") and line[2:].strip()
        ]

    @staticmethod
    def _extract_etymology(text: str) -> EtymologyInfo | None:
        """Extract etymology information."""
        if m := _ETYM_RE.search(text):
            parts = m.group(1).split("|")
            return EtymologyInfo(
                origin_language=parts[0] if parts else None,
                origin_word=parts[1] if len(parts) > 1 else None,
                relation_type="derived_from",
            )
        if m := _FROM_RE.search(text):
            return EtymologyInfo(origin_word=m.group(1), relation_type="derived_from")
        return None

    def _create_entry(self, title: str, language: str, pos: str, section_text: str) -> WiktionaryEntry | None:
        """Create a WiktionaryEntry from section text."""
        if not pos:
            return None

        entry = WiktionaryEntry(title=title, language=language, pos=pos)
        entry.definitions = self._extract_definitions(section_text)
        entry.etymology = self._extract_etymology(section_text)

        for m in _TEMPLATE_RE.finditer(section_text):
            content = m.group(1)
            parts = content.split("|")
            tname = parts[0].strip().lower()

            if "сущ" in tname or "noun" in tname:
                entry.inflections.extend(self._parse_inflection_table(parts, is_verb=False))
            elif any(x in tname for x in ("гл", "verb", "conj")):
                entry.inflections.extend(self._parse_inflection_table(parts, is_verb=True))

            if tname in ("м", "m"):
                entry.gender = "masculine"
            elif tname in ("ж", "f"):
                entry.gender = "feminine"
            elif tname in ("с", "n"):
                entry.gender = "neuter"

            if "сов" in tname or "perf" in tname:
                entry.aspect = "perfective"
            elif "несов" in tname or "imperf" in tname:
                entry.aspect = "imperfective"

        if m := _IPA_RE.search(section_text):
            entry.pronunciation = m.group(1).split("|")[0]

        return entry

    def parse_page(self, title: str, content: str, target_lang: str = "ru") -> list[WiktionaryEntry]:
        """Parse a single Wiktionary page into entries."""
        entries: list[WiktionaryEntry] = []
        in_target = False
        current_pos: str | None = None
        section_lines: list[str] = []

        def flush():
            if in_target and current_pos and section_lines:
                if e := self._create_entry(title, target_lang, current_pos, "\n".join(section_lines)):
                    entries.append(e)

        for line in content.split("\n"):
            if m := _SECTION_RE.match(line):
                level, section = len(m.group(1)), m.group(2)
                if level == 2:
                    flush()
                    in_target = section in _LANG_SECTIONS or section.lower() == target_lang
                    current_pos = None
                    section_lines = []
                elif level == 3 and in_target:
                    flush()
                    current_pos = _POS_MAP.get(section.lower().strip())
                    section_lines = []
            elif in_target and current_pos is not None:
                section_lines.append(line)

        flush()
        return entries

    def parse_dump(self, path: Path | str) -> Iterator[WiktionaryEntry]:
        """Parse a Wiktionary XML dump file."""
        for event, elem in ET.iterparse(path, events=("end",)):
            if _NS_RE.sub("", elem.tag) == "page":
                title_el = elem.find(".//{*}title")
                text_el = elem.find(".//{*}revision/{*}text")
                if title_el is not None and text_el is not None:
                    title = "".join(title_el.itertext())
                    if ":" not in title:
                        yield from self.parse_page(title, "".join(text_el.itertext()))
                elem.clear()

    def parse_file(self, path: Path | str) -> Iterator[WiktionaryEntry]:
        """Alias for parse_dump."""
        yield from self.parse_dump(path)
