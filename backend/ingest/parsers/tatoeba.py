"""Tatoeba Parser

Parses Tatoeba sentence pairs for bilingual sentence data.

Tatoeba provides:
- sentences.tar.bz2: All sentences (id, lang, text)
- links.tar.bz2: Translation links (source_id, target_id)
- sentences_detailed.tar.bz2: With username, date, etc.

Download from: https://downloads.tatoeba.org/exports/
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import csv

# ISO 639-1 (2-letter) to ISO 639-3 (3-letter) mapping for common languages
_LANG_MAP = {
    "ru": "rus", "en": "eng", "de": "deu", "fr": "fra", "es": "spa",
    "it": "ita", "pt": "por", "zh": "cmn", "ja": "jpn", "ko": "kor",
    "ar": "ara", "hi": "hin", "tr": "tur", "pl": "pol", "uk": "ukr",
    "nl": "nld", "sv": "swe", "no": "nor", "da": "dan", "fi": "fin",
}

def _normalize_lang(code: str) -> str:
    """Convert ISO 639-1 codes to ISO 639-3 (Tatoeba format)."""
    return _LANG_MAP.get(code, code)


@dataclass(slots=True)
class TatoebaSentence:
    """Single sentence from Tatoeba."""
    id: int
    language: str
    text: str
    username: str | None = None
    date_added: str | None = None
    date_modified: str | None = None


@dataclass(slots=True)
class SentencePair:
    """Paired sentences (source + translation)."""
    source: TatoebaSentence
    target: TatoebaSentence


class TatoebaParser:
    """Parser for Tatoeba TSV exports."""

    __slots__ = ("_sentences", "_links_by_source")

    def __init__(self):
        self._sentences: dict[int, TatoebaSentence] = {}
        self._links_by_source: dict[int, list[int]] = {}

    def load_sentences(self, path: Path | str, languages: set[str] | None = None) -> int:
        """Load sentences from sentences.tsv or sentences_detailed.tsv."""
        count = 0
        with open(path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) < 3 or (languages and row[1] not in languages):
                    continue
                self._sentences[int(row[0])] = TatoebaSentence(
                    id=int(row[0]),
                    language=row[1],
                    text=row[2],
                    username=row[3] if len(row) > 3 else None,
                    date_added=row[4] if len(row) > 4 else None,
                    date_modified=row[5] if len(row) > 5 else None,
                )
                count += 1
        return count

    def load_links(self, path: Path | str) -> int:
        """Load translation links from links.tsv."""
        count = 0
        with open(path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) < 2:
                    continue
                try:
                    src, tgt = int(row[0]), int(row[1])
                    self._links_by_source.setdefault(src, []).append(tgt)
                    count += 1
                except ValueError:
                    continue
        return count

    def get_pairs(self, source_lang: str, target_lang: str) -> Iterator[SentencePair]:
        """Get sentence pairs for a language combination."""
        sents = self._sentences
        for src_id, tgt_ids in self._links_by_source.items():
            if (src := sents.get(src_id)) is None:
                continue
            for tgt_id in tgt_ids:
                if (tgt := sents.get(tgt_id)) is None:
                    continue
                if src.language == source_lang and tgt.language == target_lang:
                    yield SentencePair(source=src, target=tgt)
                elif src.language == target_lang and tgt.language == source_lang:
                    yield SentencePair(source=tgt, target=src)

    def get_sentences_by_language(self, language: str) -> Iterator[TatoebaSentence]:
        """Get all sentences for a language."""
        return (s for s in self._sentences.values() if s.language == language)

    def get_sentence(self, sent_id: int) -> TatoebaSentence | None:
        """Get a sentence by ID."""
        return self._sentences.get(sent_id)

    def get_translations(self, sent_id: int, target_lang: str | None = None) -> list[TatoebaSentence]:
        """Get all translations for a sentence."""
        result = []
        sents = self._sentences
        # Check outgoing links
        for tgt_id in self._links_by_source.get(sent_id, ()):
            if (t := sents.get(tgt_id)) and (target_lang is None or t.language == target_lang):
                result.append(t)
        # Check incoming links
        for src_id, tgt_ids in self._links_by_source.items():
            if sent_id in tgt_ids and (s := sents.get(src_id)) and (target_lang is None or s.language == target_lang):
                result.append(s)
        return result

    @staticmethod
    def parse_sentences_file(path: Path | str, languages: set[str] | None = None) -> Iterator[TatoebaSentence]:
        """Parse sentences file without loading into memory."""
        with open(path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) < 3 or (languages and row[1] not in languages):
                    continue
                yield TatoebaSentence(
                    id=int(row[0]),
                    language=row[1],
                    text=row[2],
                    username=row[3] if len(row) > 3 else None,
                    date_added=row[4] if len(row) > 4 else None,
                    date_modified=row[5] if len(row) > 5 else None,
                )

    @staticmethod
    def parse_pairs_file(
        sentences_path: Path | str,
        links_path: Path | str,
        source_lang: str,
        target_lang: str,
        limit: int | None = None,
    ) -> Iterator[SentencePair]:
        """Memory-efficient parsing of sentence pairs.
        
        Two-pass algorithm:
        1. Build index of relevant sentences
        2. Stream links and yield matching pairs
        """
        # Normalize to ISO 639-3 (Tatoeba format)
        src_code = _normalize_lang(source_lang)
        tgt_code = _normalize_lang(target_lang)
        languages = {src_code, tgt_code}
        sentences: dict[int, TatoebaSentence] = {}

        with open(sentences_path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) >= 3 and row[1] in languages:
                    sid = int(row[0])
                    sentences[sid] = TatoebaSentence(id=sid, language=row[1], text=row[2])

        count = 0
        with open(links_path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) < 2:
                    continue
                try:
                    src_id, tgt_id = int(row[0]), int(row[1])
                except ValueError:
                    continue

                src, tgt = sentences.get(src_id), sentences.get(tgt_id)
                if not (src and tgt):
                    continue

                if src.language == src_code and tgt.language == tgt_code:
                    yield SentencePair(source=src, target=tgt)
                    count += 1
                elif src.language == tgt_code and tgt.language == src_code:
                    yield SentencePair(source=tgt, target=src)
                    count += 1

                if limit and count >= limit:
                    return
