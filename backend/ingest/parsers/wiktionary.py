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
from typing import Iterator, TextIO
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
    relation_type: str = "derived_from"  # derived_from, borrowed_from, cognate
    notes: str | None = None


@dataclass(slots=True)
class WiktionaryEntry:
    """Parsed Wiktionary entry for a word."""
    title: str  # Page title (word)
    language: str  # Target language (ru, en, etc.)
    pos: str  # Part of speech
    gender: str | None = None
    aspect: str | None = None  # For verbs: perfective/imperfective
    definitions: list[str] = field(default_factory=list)
    inflections: list[InflectionForm] = field(default_factory=list)
    etymology: EtymologyInfo | None = None
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    translations: dict[str, list[str]] = field(default_factory=dict)  # lang_code -> translations
    pronunciation: str | None = None  # IPA
    stress: str | None = None  # Word with stress marks
    declension_class: str | None = None
    conjugation_class: str | None = None
    extra_data: dict = field(default_factory=dict)


class WiktionaryParser:
    """Parser for Wiktionary XML dumps."""

    __slots__ = ("_namespace_pattern", "_section_pattern", "_template_pattern", "_link_pattern", "_lang_sections")

    # Russian case mappings
    CASE_MAP = {
        "им": "nominative", "именительный": "nominative", "nom": "nominative",
        "рд": "genitive", "родительный": "genitive", "gen": "genitive",
        "дт": "dative", "дательный": "dative", "dat": "dative",
        "вн": "accusative", "винительный": "accusative", "acc": "accusative",
        "тв": "instrumental", "творительный": "instrumental", "ins": "instrumental",
        "пр": "prepositional", "предложный": "prepositional", "prep": "prepositional", "loc": "prepositional",
    }

    NUMBER_MAP = {
        "ед": "singular", "единственное": "singular", "sg": "singular",
        "мн": "plural", "множественное": "plural", "pl": "plural",
    }

    GENDER_MAP = {
        "м": "masculine", "мужской": "masculine", "m": "masculine",
        "ж": "feminine", "женский": "feminine", "f": "feminine",
        "с": "neuter", "средний": "neuter", "n": "neuter",
    }

    def __init__(self):
        self._namespace_pattern = re.compile(r"\{[^}]+\}")
        self._section_pattern = re.compile(r"^(={2,})\s*(.+?)\s*\1", re.MULTILINE)
        self._template_pattern = re.compile(r"\{\{([^}]+)\}\}")
        self._link_pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
        self._lang_sections = {"Russian", "Русский", "ru"}

    def _strip_namespace(self, tag: str) -> str:
        return self._namespace_pattern.sub("", tag)

    def _extract_text(self, elem: Element | None) -> str:
        if elem is None:
            return ""
        return "".join(elem.itertext())

    def _parse_declension_table(self, template_content: str) -> list[InflectionForm]:
        """Parse a Russian declension template."""
        forms: list[InflectionForm] = []
        parts = template_content.split("|")

        if not parts:
            return forms

        # Simple noun declension pattern: {{сущ ru m |word|stem|...}}
        # Format varies, extract positional forms
        case_order = ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"]
        number_order = ["singular", "plural"]

        idx = 1  # Skip template name
        for num_idx, number in enumerate(number_order):
            for case_idx, case in enumerate(case_order):
                if idx < len(parts):
                    form_text = parts[idx].strip()
                    if form_text and form_text != "-":
                        forms.append(InflectionForm(
                            form=self._clean_form(form_text),
                            case=case,
                            number=number,
                        ))
                idx += 1

        return forms

    def _parse_conjugation_table(self, template_content: str) -> list[InflectionForm]:
        """Parse a Russian verb conjugation template."""
        forms: list[InflectionForm] = []
        parts = template_content.split("|")

        if not parts:
            return forms

        # Extract person/number forms for present/future tense
        persons = ["1st", "2nd", "3rd"]
        numbers = ["singular", "plural"]

        idx = 1
        for number in numbers:
            for person in persons:
                if idx < len(parts):
                    form_text = parts[idx].strip()
                    if form_text and form_text != "-":
                        forms.append(InflectionForm(
                            form=self._clean_form(form_text),
                            person=person,
                            number=number,
                            tense="present",
                        ))
                idx += 1

        return forms

    def _clean_form(self, text: str) -> str:
        """Clean a word form from wiki markup."""
        # Remove links
        text = self._link_pattern.sub(r"\1", text)
        # Remove remaining markup
        text = re.sub(r"[']{2,}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def _extract_definitions(self, text: str) -> list[str]:
        """Extract definitions from wiki text."""
        definitions = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("# *"):
                definition = line[2:].strip()
                definition = self._clean_form(definition)
                if definition:
                    definitions.append(definition)
        return definitions

    def _extract_etymology(self, text: str) -> EtymologyInfo | None:
        """Extract etymology information."""
        # Look for etymology templates
        etym_match = re.search(r"\{\{этимология\|([^}]+)\}\}", text)
        if etym_match:
            parts = etym_match.group(1).split("|")
            if parts:
                return EtymologyInfo(
                    origin_language=parts[0] if parts else None,
                    origin_word=parts[1] if len(parts) > 1 else None,
                    relation_type="derived_from",
                )

        # Look for "от" (from) patterns
        from_match = re.search(r"от\s+\[\[([^\]]+)\]\]", text)
        if from_match:
            return EtymologyInfo(
                origin_word=from_match.group(1),
                relation_type="derived_from",
            )

        return None

    def _parse_pos(self, section_title: str) -> str | None:
        """Map section title to part of speech."""
        pos_map = {
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
        lower_title = section_title.lower().strip()
        return pos_map.get(lower_title)

    def parse_page(self, title: str, content: str, target_lang: str = "ru") -> list[WiktionaryEntry]:
        """Parse a single Wiktionary page into entries."""
        entries: list[WiktionaryEntry] = []

        # Find language sections
        sections = self._section_pattern.findall(content)
        in_target_lang = False
        current_pos: str | None = None
        current_section_text: list[str] = []

        lines = content.split("\n")
        for line in lines:
            section_match = self._section_pattern.match(line)
            if section_match:
                level = len(section_match.group(1))
                section_title = section_match.group(2)

                if level == 2:
                    # Language section
                    if in_target_lang and current_pos and current_section_text:
                        entry = self._create_entry(title, target_lang, current_pos, "\n".join(current_section_text))
                        if entry:
                            entries.append(entry)

                    in_target_lang = section_title in self._lang_sections or section_title.lower() == target_lang
                    current_pos = None
                    current_section_text = []

                elif level == 3 and in_target_lang:
                    # POS section
                    if current_pos and current_section_text:
                        entry = self._create_entry(title, target_lang, current_pos, "\n".join(current_section_text))
                        if entry:
                            entries.append(entry)

                    current_pos = self._parse_pos(section_title)
                    current_section_text = []

            elif in_target_lang and current_pos is not None:
                current_section_text.append(line)

        # Handle last entry
        if in_target_lang and current_pos and current_section_text:
            entry = self._create_entry(title, target_lang, current_pos, "\n".join(current_section_text))
            if entry:
                entries.append(entry)

        return entries

    def _create_entry(self, title: str, language: str, pos: str, section_text: str) -> WiktionaryEntry | None:
        """Create a WiktionaryEntry from section text."""
        if not pos:
            return None

        entry = WiktionaryEntry(title=title, language=language, pos=pos)

        # Extract definitions
        entry.definitions = self._extract_definitions(section_text)

        # Extract etymology
        entry.etymology = self._extract_etymology(section_text)

        # Extract inflections from templates
        for template_match in self._template_pattern.finditer(section_text):
            template_content = template_match.group(1)
            template_name = template_content.split("|")[0].strip().lower()

            if "сущ" in template_name or "noun" in template_name:
                entry.inflections.extend(self._parse_declension_table(template_content))
            elif "гл" in template_name or "verb" in template_name or "conj" in template_name:
                entry.inflections.extend(self._parse_conjugation_table(template_content))

            # Extract gender
            if template_name in ("м", "m"):
                entry.gender = "masculine"
            elif template_name in ("ж", "f"):
                entry.gender = "feminine"
            elif template_name in ("с", "n"):
                entry.gender = "neuter"

            # Extract aspect
            if "сов" in template_name or "perf" in template_name:
                entry.aspect = "perfective"
            elif "несов" in template_name or "imperf" in template_name:
                entry.aspect = "imperfective"

        # Extract pronunciation (IPA)
        ipa_match = re.search(r"\{\{IPA\|([^}]+)\}\}", section_text)
        if ipa_match:
            entry.pronunciation = ipa_match.group(1).split("|")[0]

        return entry

    def parse_dump(self, path: Path | str) -> Iterator[WiktionaryEntry]:
        """Parse a Wiktionary XML dump file."""
        context = ET.iterparse(path, events=("end",))

        for event, elem in context:
            tag = self._strip_namespace(elem.tag)

            if tag == "page":
                # Extract title and content
                title_elem = elem.find(".//{*}title")
                text_elem = elem.find(".//{*}revision/{*}text")

                if title_elem is not None and text_elem is not None:
                    title = self._extract_text(title_elem)
                    content = self._extract_text(text_elem)

                    # Skip non-content pages
                    if ":" not in title:
                        yield from self.parse_page(title, content)

                # Clear element to save memory
                elem.clear()

    def parse_file(self, path: Path | str) -> Iterator[WiktionaryEntry]:
        """Alias for parse_dump."""
        yield from self.parse_dump(path)

