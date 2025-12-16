"""Ingestion Pipeline

Orchestrates the full data ingestion process:
1. Parse source files (UD, Wiktionary, Tatoeba)
2. Extract and deduplicate patterns
3. Calculate complexity scores
4. Create sentences and link to patterns
5. Track ingestion records
"""
from datetime import datetime
from pathlib import Path
from uuid import UUID
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from models.srs import Sentence, SyntacticPattern, SentencePattern
from models.morphology import Lemma, Inflection
from models.etymology import EtymologyNode, EtymologyRelation
from models.datasource import IngestionRecord, ExternalIdMapping
from ingest.parsers.conllu import CoNLLUParser, UDSentence
from ingest.parsers.wiktionary import WiktionaryParser, WiktionaryEntry
from ingest.parsers.tatoeba import TatoebaParser, SentencePair
from ingest.complexity import ComplexityScorer

# Difficulty lookup by grammatical feature
_CASE_DIFF = {"nominative": 1, "accusative": 2, "genitive": 4, "dative": 5, "instrumental": 6, "prepositional": 4}
_FEATURE_PARSE = {"nominative", "genitive", "dative", "accusative", "instrumental", "prepositional",
                  "singular", "plural", "masculine", "feminine", "neuter", "present", "past", "future"}


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
    """Main ingestion orchestrator."""

    __slots__ = ("language", "batch_size", "_pattern_cache", "_lemma_cache", "_scorer")

    def __init__(self, language: str = "ru", batch_size: int = 100):
        self.language = language
        self.batch_size = batch_size
        self._pattern_cache: dict[tuple, UUID] = {}
        self._lemma_cache: dict[str, UUID] = {}
        self._scorer: ComplexityScorer | None = None

    async def _get_or_create_pattern(self, session: AsyncSession, pattern_type: str, features: dict) -> UUID:
        """Get existing pattern or create new one."""
        cache_key = (pattern_type, tuple(sorted(features.items())))
        if pid := self._pattern_cache.get(cache_key):
            return pid

        result = await session.execute(
            select(SyntacticPattern).where(
                SyntacticPattern.pattern_type == pattern_type,
                SyntacticPattern.language == self.language,
            )
        )
        if pattern := result.scalar_one_or_none():
            self._pattern_cache[cache_key] = pattern.id
            return pattern.id

        pattern = SyntacticPattern(
            pattern_type=pattern_type,
            language=self.language,
            features=features,
            difficulty=self._estimate_difficulty(pattern_type),
        )
        session.add(pattern)
        await session.flush()
        self._pattern_cache[cache_key] = pattern.id
        return pattern.id

    @staticmethod
    def _estimate_difficulty(pattern_type: str) -> int:
        """Estimate difficulty for a new pattern (1-10)."""
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

    async def _create_mapping(
        self, session: AsyncSession, source: str, ext_id: str, entity: str, internal_id: UUID, checksum: str | None = None
    ) -> None:
        """Create mapping from external ID to internal ID."""
        session.add(ExternalIdMapping(
            source_name=source, external_id=ext_id, entity_type=entity, internal_id=internal_id, checksum=checksum
        ))

    async def _get_mapping(self, session: AsyncSession, source: str, ext_id: str, entity: str) -> UUID | None:
        """Get existing internal ID for an external ID."""
        result = await session.execute(
            select(ExternalIdMapping.internal_id).where(
                ExternalIdMapping.source_name == source,
                ExternalIdMapping.external_id == ext_id,
                ExternalIdMapping.entity_type == entity,
            )
        )
        return result.scalar_one_or_none()

    async def ingest_ud_corpus(
        self, conllu_path: Path | str, progress_callback: Callable[[int, int], Awaitable[None]] | None = None
    ) -> IngestionStats:
        """Ingest sentences and patterns from Universal Dependencies corpus."""
        stats = IngestionStats()
        source = "universal_dependencies"
        sentences = list(CoNLLUParser().parse_file(conllu_path))
        total = len(sentences)
        self._scorer = ComplexityScorer.from_corpus(sentences)

        async with get_db_session() as session:
            record = IngestionRecord(
                source_name=source, language=self.language, file_path=str(conllu_path),
                status="running", started_at=datetime.utcnow()
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[UDSentence] = []
                for ud in sentences:
                    batch.append(ud)
                    if len(batch) >= self.batch_size:
                        await self._process_ud_batch(session, batch, source, stats)
                        batch = []
                        if progress_callback:
                            await progress_callback(stats.records_processed, total)
                if batch:
                    await self._process_ud_batch(session, batch, source, stats)

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
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        return stats

    async def _process_ud_batch(self, session: AsyncSession, batch: list[UDSentence], source: str, stats: IngestionStats) -> None:
        """Process a batch of UD sentences."""
        for ud in batch:
            stats.records_processed += 1
            try:
                if await self._get_mapping(session, source, ud.sent_id, "sentence"):
                    stats.records_skipped += 1
                    continue

                sent = Sentence(
                    text=ud.text,
                    language=self.language,
                    complexity_score=self._scorer.score(ud) if self._scorer else 5,
                    source=source,
                    extra_data={"sent_id": ud.sent_id, "metadata": ud.metadata},
                )
                session.add(sent)
                await session.flush()
                await self._create_mapping(session, source, ud.sent_id, "sentence", sent.id)

                for key, pos in ud.get_pattern_positions():
                    parts = key.split("_")
                    feats: dict[str, str] = {"raw_key": key}
                    if len(parts) >= 2:
                        feats["upos"] = parts[0]
                    for p in parts[1:]:
                        if p in _FEATURE_PARSE:
                            if p in {"nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"}:
                                feats["case"] = p
                            elif p in {"singular", "plural"}:
                                feats["number"] = p
                            elif p in {"masculine", "feminine", "neuter"}:
                                feats["gender"] = p
                            elif p in {"present", "past", "future"}:
                                feats["tense"] = p

                    pid = await self._get_or_create_pattern(session, key, feats)
                    session.add(SentencePattern(sentence_id=sent.id, pattern_id=pid, position=pos))

                stats.records_created += 1
            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Sentence {ud.sent_id}: {e}")

    async def ingest_wiktionary(
        self, dump_path: Path | str, progress_callback: Callable[[int, int], Awaitable[None]] | None = None
    ) -> IngestionStats:
        """Ingest lemmas and inflections from Wiktionary dump."""
        stats = IngestionStats()
        source = "wiktionary"

        async with get_db_session() as session:
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
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        return stats

    async def _process_wikt_batch(self, session: AsyncSession, batch: list[WiktionaryEntry], source: str, stats: IngestionStats) -> None:
        """Process a batch of Wiktionary entries."""
        for entry in batch:
            stats.records_processed += 1
            try:
                ext_id = f"{entry.title}:{entry.pos}"
                if await self._get_mapping(session, source, ext_id, "lemma"):
                    stats.records_skipped += 1
                    continue

                lemma = Lemma(
                    word=entry.title,
                    language=self.language,
                    part_of_speech=entry.pos,
                    gender=entry.gender,
                    aspect=entry.aspect,
                    declension_class=entry.declension_class,
                    conjugation_class=entry.conjugation_class,
                    definition="; ".join(entry.definitions) if entry.definitions else None,
                    features={"synonyms": entry.synonyms, "antonyms": entry.antonyms, "pronunciation": entry.pronunciation},
                )
                session.add(lemma)
                await session.flush()
                await self._create_mapping(session, source, ext_id, "lemma", lemma.id)

                for inf in entry.inflections:
                    session.add(Inflection(
                        lemma_id=lemma.id, form=inf.form, case=inf.case, number=inf.number,
                        person=inf.person, tense=inf.tense, gender=inf.gender,
                        features={"mood": inf.mood, "aspect": inf.aspect},
                    ))

                if (et := entry.etymology) and et.origin_word:
                    origin = EtymologyNode(
                        word=et.origin_word,
                        language=et.origin_language or "unknown",
                        is_reconstructed="Y" if et.origin_word.startswith("*") else "N",
                    )
                    session.add(origin)
                    await session.flush()

                    current = EtymologyNode(
                        word=entry.title,
                        language=self.language,
                        part_of_speech=entry.pos,
                        meaning=entry.definitions[0] if entry.definitions else None,
                    )
                    session.add(current)
                    await session.flush()
                    session.add(EtymologyRelation(source_id=origin.id, target_id=current.id, relation_type=et.relation_type))

                stats.records_created += 1
            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Entry {entry.title}: {e}")

    async def ingest_tatoeba(
        self,
        sentences_path: Path | str,
        links_path: Path | str,
        target_lang: str = "en",
        limit: int | None = None,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> IngestionStats:
        """Ingest sentence translations from Tatoeba."""
        stats = IngestionStats()
        source = "tatoeba"

        async with get_db_session() as session:
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
                        await self._process_tatoeba_batch(session, batch, source, stats)
                        batch = []
                        if progress_callback:
                            await progress_callback(stats.records_processed, limit or -1)
                if batch:
                    await self._process_tatoeba_batch(session, batch, source, stats)

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
                raise
            finally:
                await session.commit()

        stats.completed_at = datetime.utcnow()
        return stats

    async def _process_tatoeba_batch(self, session: AsyncSession, batch: list[SentencePair], source: str, stats: IngestionStats) -> None:
        """Process a batch of Tatoeba sentence pairs."""
        for pair in batch:
            stats.records_processed += 1
            try:
                ext_id = str(pair.source.id)
                if existing := await self._get_mapping(session, source, ext_id, "sentence"):
                    result = await session.execute(select(Sentence).where(Sentence.id == existing))
                    if (sent := result.scalar_one_or_none()) and not sent.translation:
                        sent.translation = pair.target.text
                        stats.records_updated += 1
                    else:
                        stats.records_skipped += 1
                    continue

                result = await session.execute(
                    select(Sentence).where(Sentence.text == pair.source.text, Sentence.language == self.language)
                )
                if sent := result.scalar_one_or_none():
                    if not sent.translation:
                        sent.translation = pair.target.text
                        stats.records_updated += 1
                    else:
                        stats.records_skipped += 1
                else:
                    sent = Sentence(
                        text=pair.source.text,
                        language=self.language,
                        translation=pair.target.text,
                        complexity_score=5,
                        source=source,
                        extra_data={"tatoeba_id": pair.source.id, "translation_id": pair.target.id},
                    )
                    session.add(sent)
                    await session.flush()
                    await self._create_mapping(session, source, ext_id, "sentence", sent.id)
                    stats.records_created += 1
            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Pair {pair.source.id}: {e}")
