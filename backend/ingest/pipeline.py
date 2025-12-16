"""Ingestion Pipeline - High Performance

Optimized for maximum throughput:
1. Pre-loaded caches eliminate N+1 queries
2. Bulk inserts with add_all for minimal round-trips
3. Streaming parsing with incremental complexity scoring
4. Efficient batch processing with configurable size
"""
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Callable, Awaitable
from collections import defaultdict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from core.logging import db_logger

log = db_logger()
from models.srs import Sentence, SyntacticPattern, SentencePattern
from models.morphology import Lemma, Inflection
from models.etymology import EtymologyNode, EtymologyRelation
from models.datasource import IngestionRecord, ExternalIdMapping
from ingest.parsers.conllu import CoNLLUParser, UDSentence
from ingest.parsers.wiktionary import WiktionaryParser, WiktionaryEntry
from ingest.parsers.tatoeba import TatoebaParser, SentencePair
from ingest.complexity import ComplexityScorer

# Feature parsing constants (use full names from curriculum)
_CASE_DIFF = {"nominative": 1, "accusative": 2, "genitive": 4, "dative": 5, "instrumental": 6, "prepositional": 4}
_CASES = {"nominative", "genitive", "dative", "accusative", "instrumental", "prepositional", "vocative", "partitive"}
_NUMBERS = {"singular", "plural", "dual"}
_GENDERS = {"masculine", "feminine", "neuter"}
_TENSES = {"present", "past", "future"}
_ASPECTS = {"imperfective", "perfective"}
_MOODS = {"indicative", "imperative", "subjunctive", "conditional"}


@dataclass
class IngestionStats:
    """Statistics for an ingestion run."""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_failed": self.records_failed,
            "error_count": len(self.errors),
        }


class IngestionPipeline:
    """High-performance ingestion orchestrator with bulk operations."""

    __slots__ = ("language", "batch_size", "_pattern_cache", "_mapping_cache", "_scorer",
                 "_pattern_freq", "_lemma_freq")

    def __init__(self, language: str = "ru", batch_size: int = 500):
        self.language = language
        self.batch_size = batch_size
        self._pattern_cache: dict[str, UUID] = {}
        self._mapping_cache: set[str] = set()
        self._scorer: ComplexityScorer | None = None
        self._pattern_freq: dict[str, int] = defaultdict(int)
        self._lemma_freq: dict[str, int] = defaultdict(int)

    async def _preload_caches(self, session: AsyncSession, source_name: str) -> None:
        """Pre-load all existing patterns and mappings to avoid N+1 queries."""
        # Load all patterns for language
        result = await session.execute(
            select(SyntacticPattern.pattern_type, SyntacticPattern.id)
            .where(SyntacticPattern.language == self.language)
        )
        self._pattern_cache = {row[0]: row[1] for row in result.fetchall()}

        # Load all external mappings for source
        result = await session.execute(
            select(ExternalIdMapping.external_id, ExternalIdMapping.entity_type)
            .where(ExternalIdMapping.source_name == source_name)
        )
        self._mapping_cache = {f"{row[0]}:{row[1]}" for row in result.fetchall()}

    def _mapping_exists(self, external_id: str, entity_type: str) -> bool:
        return f"{external_id}:{entity_type}" in self._mapping_cache

    def _cache_mapping(self, external_id: str, entity_type: str) -> None:
        self._mapping_cache.add(f"{external_id}:{entity_type}")

    @staticmethod
    def _estimate_difficulty(pattern_type: str) -> int:
        """Estimate difficulty for a pattern (1-10)."""
        parts = pattern_type.lower().split("_")
        diff = 3
        for case, d in _CASE_DIFF.items():
            if case in parts:
                diff = max(diff, d)
                break
        if "verb" in parts:
            diff = max(diff, 3)
            if "past" in parts:
                diff = max(diff, 4)
            if "subjunctive" in parts or "conditional" in parts:
                diff = max(diff, 7)
            if "passive" in parts:
                diff = max(diff, 6)
        if "plural" in parts:
            diff = min(diff + 1, 10)
        return diff

    @staticmethod
    def _parse_features(pattern_key: str) -> dict[str, str]:
        """Parse features from pattern key."""
        parts = pattern_key.split("_")
        feats: dict[str, str] = {"raw_key": pattern_key}
        if parts:
            feats["upos"] = parts[0]
        for p in parts[1:]:
            if p in _CASES:
                feats["case"] = p
            elif p in _NUMBERS:
                feats["number"] = p
            elif p in _GENDERS:
                feats["gender"] = p
            elif p in _TENSES:
                feats["tense"] = p
            elif p in _ASPECTS:
                feats["aspect"] = p
            elif p in _MOODS:
                feats["mood"] = p
            elif p in ("1st", "2nd", "3rd"):
                feats["person"] = p
        return feats

    def _build_scorer(self, sentences: list[UDSentence]) -> ComplexityScorer:
        """Build scorer from corpus, collecting frequencies."""
        total = len(sentences)
        for s in sentences:
            for p in s.get_patterns():
                self._pattern_freq[p] += 1
            for l in s.lemmas:
                self._lemma_freq[l] += 1

        pattern_frequencies = {p: c / total for p, c in self._pattern_freq.items()}
        sorted_lemmas = sorted(self._lemma_freq.items(), key=lambda x: -x[1])
        lemma_frequencies = {l: r + 1 for r, (l, _) in enumerate(sorted_lemmas)}
        return ComplexityScorer(pattern_frequencies=pattern_frequencies, lemma_frequencies=lemma_frequencies)

    async def ingest_ud_corpus(
        self, conllu_path: Path | str, progress_callback: Callable[[int, int], Awaitable[None]] | None = None
    ) -> IngestionStats:
        """Ingest UD corpus with bulk operations."""
        stats = IngestionStats()
        source = "universal_dependencies"
        log.info("ud_ingestion_started", file_path=str(conllu_path), language=self.language)

        # Parse all sentences first for complexity calibration
        sentences = list(CoNLLUParser().parse_file(conllu_path))
        total = len(sentences)
        self._scorer = self._build_scorer(sentences)

        async with get_db_session() as session:
            await self._preload_caches(session, source)

            record = IngestionRecord(
                source_name=source, language=self.language, file_path=str(conllu_path),
                status="running", started_at=datetime.utcnow()
            )
            session.add(record)
            await session.flush()

            try:
                for i in range(0, total, self.batch_size):
                    batch = sentences[i:i + self.batch_size]
                    await self._process_ud_batch(session, batch, source, stats)
                    if progress_callback:
                        await progress_callback(stats.records_processed, total)

                await session.commit()
                record.status = "completed"
                record.completed_at = datetime.utcnow()
                record.records_processed = stats.records_processed
                record.records_created = stats.records_created
                record.records_updated = stats.records_updated
                record.records_skipped = stats.records_skipped
                record.records_failed = stats.records_failed
            except Exception as e:
                await session.rollback()
                record.status = "failed"
                record.error_log = [str(e)]
                stats.errors.append(str(e))
                log.error("ud_ingestion_failed", error=str(e), records_processed=stats.records_processed)
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        log.info("ud_ingestion_completed", records_created=stats.records_created, records_skipped=stats.records_skipped)
        return stats

    async def _process_ud_batch(
        self, session: AsyncSession, batch: list[UDSentence], source: str, stats: IngestionStats
    ) -> None:
        """Process batch with ORM bulk operations."""
        new_patterns: list[SyntacticPattern] = []
        new_sentences: list[Sentence] = []
        new_mappings: list[ExternalIdMapping] = []
        new_links: list[SentencePattern] = []

        for ud in batch:
            stats.records_processed += 1

            if self._mapping_exists(ud.sent_id, "sentence"):
                stats.records_skipped += 1
                continue

            try:
                sent_id = uuid4()
                complexity = self._scorer.score(ud) if self._scorer else 5

                new_sentences.append(Sentence(
                    id=sent_id, text=ud.text, language=self.language,
                    complexity_score=complexity, source=source,
                    extra_data={"sent_id": ud.sent_id, "metadata": ud.metadata}
                ))

                new_mappings.append(ExternalIdMapping(
                    source_name=source, external_id=ud.sent_id,
                    entity_type="sentence", internal_id=sent_id
                ))
                self._cache_mapping(ud.sent_id, "sentence")

                for key, pos in ud.get_pattern_positions():
                    if not key:  # Skip empty patterns
                        continue
                    if key not in self._pattern_cache:
                        pattern_id = uuid4()
                        pattern = SyntacticPattern(
                            id=pattern_id,
                            pattern_type=key, language=self.language,
                            features=self._parse_features(key),
                            difficulty=self._estimate_difficulty(key)
                        )
                        new_patterns.append(pattern)
                        self._pattern_cache[key] = pattern_id

                    new_links.append(SentencePattern(
                        sentence_id=sent_id,
                        pattern_id=self._pattern_cache[key],
                        position=pos
                    ))

                stats.records_created += 1
            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Sentence {ud.sent_id}: {e}")

        # Bulk add all objects
        if new_patterns:
            session.add_all(new_patterns)
            await session.flush()  # Get IDs assigned
        if new_sentences:
            session.add_all(new_sentences)
        if new_mappings:
            session.add_all(new_mappings)
        if new_links:
            session.add_all(new_links)
        
        await session.flush()

    async def ingest_tatoeba(
        self,
        sentences_path: Path | str,
        links_path: Path | str,
        target_lang: str = "en",
        limit: int | None = None,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> IngestionStats:
        """Ingest Tatoeba with bulk operations."""
        stats = IngestionStats()
        source = "tatoeba"
        log.info("tatoeba_ingestion_started", sentences_path=str(sentences_path), language=self.language, limit=limit)

        async with get_db_session() as session:
            await self._preload_caches(session, source)

            # Pre-load existing sentences by text for matching
            result = await session.execute(
                select(Sentence.id, Sentence.text, Sentence.translation)
                .where(Sentence.language == self.language)
            )
            existing_sentences = {row[1]: (row[0], row[2]) for row in result.fetchall()}

            record = IngestionRecord(
                source_name=source, language=self.language, file_path=str(sentences_path),
                status="running", started_at=datetime.utcnow()
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[SentencePair] = []
                pairs = TatoebaParser.parse_pairs_file(sentences_path, links_path, self.language, target_lang, limit)

                for pair in pairs:
                    batch.append(pair)
                    if len(batch) >= self.batch_size:
                        await self._process_tatoeba_batch(session, batch, source, stats, existing_sentences)
                        batch = []
                        if progress_callback:
                            await progress_callback(stats.records_processed, limit or -1)

                if batch:
                    await self._process_tatoeba_batch(session, batch, source, stats, existing_sentences)

                await session.commit()
                record.status = "completed"
                record.completed_at = datetime.utcnow()
                record.records_processed = stats.records_processed
                record.records_created = stats.records_created
                record.records_updated = stats.records_updated
            except Exception as e:
                await session.rollback()
                record.status = "failed"
                record.error_log = [str(e)]
                stats.errors.append(str(e))
                log.error("tatoeba_ingestion_failed", error=str(e), records_processed=stats.records_processed)
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        log.info("tatoeba_ingestion_completed", records_created=stats.records_created, records_updated=stats.records_updated)
        return stats

    async def _process_tatoeba_batch(
        self, session: AsyncSession, batch: list[SentencePair], source: str,
        stats: IngestionStats, existing_sentences: dict[str, tuple[UUID, str | None]]
    ) -> None:
        """Process Tatoeba batch with ORM bulk operations."""
        new_sentences: list[Sentence] = []
        new_mappings: list[ExternalIdMapping] = []
        updates: list[tuple[UUID, str]] = []

        for pair in batch:
            stats.records_processed += 1
            ext_id = str(pair.source.id)

            try:
                if self._mapping_exists(ext_id, "sentence"):
                    stats.records_skipped += 1
                    continue

                if pair.source.text in existing_sentences:
                    sent_id, existing_trans = existing_sentences[pair.source.text]
                    if not existing_trans:
                        updates.append((sent_id, pair.target.text))
                        stats.records_updated += 1
                    else:
                        stats.records_skipped += 1
                    continue

                sent_id = uuid4()
                new_sentences.append(Sentence(
                    id=sent_id, text=pair.source.text, language=self.language,
                    translation=pair.target.text, complexity_score=5, source=source,
                    extra_data={"tatoeba_id": pair.source.id, "translation_id": pair.target.id}
                ))

                new_mappings.append(ExternalIdMapping(
                    source_name=source, external_id=ext_id,
                    entity_type="sentence", internal_id=sent_id
                ))
                self._cache_mapping(ext_id, "sentence")
                existing_sentences[pair.source.text] = (sent_id, pair.target.text)
                stats.records_created += 1

            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Pair {pair.source.id}: {e}")

        # Bulk add
        if new_sentences:
            session.add_all(new_sentences)
        if new_mappings:
            session.add_all(new_mappings)

        # Bulk update translations using ORM
        for sent_id, translation in updates:
            await session.execute(
                update(Sentence).where(Sentence.id == sent_id).values(translation=translation)
            )

        await session.flush()

    async def ingest_wiktionary(
        self, dump_path: Path | str, progress_callback: Callable[[int, int], Awaitable[None]] | None = None
    ) -> IngestionStats:
        """Ingest Wiktionary with bulk operations."""
        stats = IngestionStats()
        source = "wiktionary"
        log.info("wiktionary_ingestion_started", dump_path=str(dump_path), language=self.language)

        async with get_db_session() as session:
            await self._preload_caches(session, source)

            record = IngestionRecord(
                source_name=source, language=self.language, file_path=str(dump_path),
                status="running", started_at=datetime.utcnow()
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[WiktionaryEntry] = []
                for entry in WiktionaryParser().parse_dump(dump_path):
                    if entry.language != self.language:
                        continue
                    batch.append(entry)
                    if len(batch) >= self.batch_size:
                        await self._process_wikt_batch(session, batch, source, stats)
                        batch = []
                        if progress_callback:
                            await progress_callback(stats.records_processed, -1)

                if batch:
                    await self._process_wikt_batch(session, batch, source, stats)

                await session.commit()
                record.status = "completed"
                record.completed_at = datetime.utcnow()
                record.records_processed = stats.records_processed
                record.records_created = stats.records_created
            except Exception as e:
                await session.rollback()
                record.status = "failed"
                record.error_log = [str(e)]
                stats.errors.append(str(e))
                log.error("wiktionary_ingestion_failed", error=str(e), records_processed=stats.records_processed)
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        log.info("wiktionary_ingestion_completed", records_created=stats.records_created, records_skipped=stats.records_skipped)
        return stats

    async def _process_wikt_batch(
        self, session: AsyncSession, batch: list[WiktionaryEntry], source: str, stats: IngestionStats
    ) -> None:
        """Process Wiktionary batch with ORM bulk operations."""
        new_lemmas: list[Lemma] = []
        new_inflections: list[Inflection] = []
        new_mappings: list[ExternalIdMapping] = []

        for entry in batch:
            stats.records_processed += 1
            ext_id = f"{entry.title}:{entry.pos}"

            if self._mapping_exists(ext_id, "lemma"):
                stats.records_skipped += 1
                continue

            try:
                lemma = Lemma(
                    word=entry.title, language=self.language,
                    part_of_speech=entry.pos, gender=entry.gender, aspect=entry.aspect,
                    declension_class=entry.declension_class, conjugation_class=entry.conjugation_class,
                    definition="; ".join(entry.definitions) if entry.definitions else None,
                    features={"synonyms": entry.synonyms, "antonyms": entry.antonyms, "pronunciation": entry.pronunciation}
                )
                new_lemmas.append(lemma)

                new_mappings.append(ExternalIdMapping(
                    source_name=source, external_id=ext_id,
                    entity_type="lemma", internal_id=lemma.id
                ))
                self._cache_mapping(ext_id, "lemma")

                for inf in entry.inflections:
                    new_inflections.append(Inflection(
                        lemma_id=lemma.id, form=inf.form,
                        case=inf.case, number=inf.number, person=inf.person,
                        tense=inf.tense, gender=inf.gender,
                        features={"mood": inf.mood, "aspect": inf.aspect}
                    ))

                stats.records_created += 1
            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Entry {entry.title}: {e}")

        # Bulk add
        if new_lemmas:
            session.add_all(new_lemmas)
        if new_mappings:
            session.add_all(new_mappings)
        if new_inflections:
            session.add_all(new_inflections)

        await session.flush()
