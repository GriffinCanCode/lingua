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

    __slots__ = ("_sentences", "_links")

    def __init__(self):
        self._sentences: dict[int, TatoebaSentence] = {}
        self._links: list[tuple[int, int]] = []

    def load_sentences(self, path: Path | str, languages: set[str] | None = None) -> int:
        """Load sentences from sentences.tsv or sentences_detailed.tsv.
        
        Returns count of loaded sentences.
        """
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 3:
                    continue

                lang = row[1]
                if languages and lang not in languages:
                    continue

                sent_id = int(row[0])
                text = row[2]

                # Detailed format has more columns
                username = row[3] if len(row) > 3 else None
                date_added = row[4] if len(row) > 4 else None
                date_modified = row[5] if len(row) > 5 else None

                self._sentences[sent_id] = TatoebaSentence(
                    id=sent_id,
                    language=lang,
                    text=text,
                    username=username,
                    date_added=date_added,
                    date_modified=date_modified,
                )
                count += 1

        return count

    def load_links(self, path: Path | str) -> int:
        """Load translation links from links.tsv.
        
        Returns count of loaded links.
        """
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) >= 2:
                    try:
                        source_id = int(row[0])
                        target_id = int(row[1])
                        self._links.append((source_id, target_id))
                        count += 1
                    except ValueError:
                        continue
        return count

    def get_pairs(self, source_lang: str, target_lang: str) -> Iterator[SentencePair]:
        """Get sentence pairs for a language combination."""
        for source_id, target_id in self._links:
            source = self._sentences.get(source_id)
            target = self._sentences.get(target_id)

            if source and target:
                if source.language == source_lang and target.language == target_lang:
                    yield SentencePair(source=source, target=target)
                elif source.language == target_lang and target.language == source_lang:
                    yield SentencePair(source=target, target=source)

    def get_sentences_by_language(self, language: str) -> Iterator[TatoebaSentence]:
        """Get all sentences for a language."""
        for sent in self._sentences.values():
            if sent.language == language:
                yield sent

    def get_sentence(self, sent_id: int) -> TatoebaSentence | None:
        """Get a sentence by ID."""
        return self._sentences.get(sent_id)

    def get_translations(self, sent_id: int, target_lang: str | None = None) -> list[TatoebaSentence]:
        """Get all translations for a sentence."""
        translations = []
        for source_id, target_id in self._links:
            if source_id == sent_id:
                target = self._sentences.get(target_id)
                if target and (target_lang is None or target.language == target_lang):
                    translations.append(target)
            elif target_id == sent_id:
                source = self._sentences.get(source_id)
                if source and (target_lang is None or source.language == target_lang):
                    translations.append(source)
        return translations

    @staticmethod
    def parse_sentences_file(path: Path | str, languages: set[str] | None = None) -> Iterator[TatoebaSentence]:
        """Parse sentences file without loading into memory."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 3:
                    continue

                lang = row[1]
                if languages and lang not in languages:
                    continue

                yield TatoebaSentence(
                    id=int(row[0]),
                    language=lang,
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
        # Load only relevant sentences
        sentences: dict[int, TatoebaSentence] = {}
        languages = {source_lang, target_lang}

        with open(sentences_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) >= 3 and row[1] in languages:
                    sentences[int(row[0])] = TatoebaSentence(
                        id=int(row[0]),
                        language=row[1],
                        text=row[2],
                    )

        # Stream links and yield pairs
        count = 0
        with open(links_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 2:
                    continue

                try:
                    source_id = int(row[0])
                    target_id = int(row[1])
                except ValueError:
                    continue

                source = sentences.get(source_id)
                target = sentences.get(target_id)

                if source and target:
                    if source.language == source_lang and target.language == target_lang:
                        yield SentencePair(source=source, target=target)
                        count += 1
                    elif source.language == target_lang and target.language == source_lang:
                        yield SentencePair(source=target, target=source)
                        count += 1

                    if limit and count >= limit:
                        return

