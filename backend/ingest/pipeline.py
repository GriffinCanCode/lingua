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
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Callable, Awaitable
import hashlib
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from models.srs import Sentence, SyntacticPattern, SentencePattern
from models.morphology import Lemma, Inflection, MorphologicalRule
from models.etymology import EtymologyNode, EtymologyRelation
from models.datasource import DataSource, IngestionRecord, ExternalIdMapping
from ingest.parsers.conllu import CoNLLUParser, UDSentence
from ingest.parsers.wiktionary import WiktionaryParser, WiktionaryEntry
from ingest.parsers.tatoeba import TatoebaParser, SentencePair
from ingest.complexity import ComplexityScorer


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
        self._pattern_cache: dict[str, UUID] = {}
        self._lemma_cache: dict[str, UUID] = {}
        self._scorer: ComplexityScorer | None = None

    async def _get_or_create_pattern(
        self,
        session: AsyncSession,
        pattern_type: str,
        features: dict,
    ) -> UUID:
        """Get existing pattern or create new one."""
        cache_key = f"{pattern_type}:{hashlib.md5(str(features).encode()).hexdigest()}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        # Check database
        result = await session.execute(
            select(SyntacticPattern).where(
                SyntacticPattern.pattern_type == pattern_type,
                SyntacticPattern.language == self.language,
            )
        )
        pattern = result.scalar_one_or_none()

        if pattern:
            self._pattern_cache[cache_key] = pattern.id
            return pattern.id

        # Create new pattern
        pattern = SyntacticPattern(
            pattern_type=pattern_type,
            language=self.language,
            features=features,
            difficulty=self._estimate_pattern_difficulty(pattern_type),
        )
        session.add(pattern)
        await session.flush()

        self._pattern_cache[cache_key] = pattern.id
        return pattern.id

    def _estimate_pattern_difficulty(self, pattern_type: str) -> int:
        """Estimate difficulty for a new pattern (1-10)."""
        # Base difficulty by grammatical complexity
        difficulty = 3  # Default medium

        parts = pattern_type.lower().split("_")

        # Case-based adjustments
        case_difficulty = {
            "nominative": 1, "accusative": 2, "genitive": 4,
            "dative": 5, "instrumental": 6, "prepositional": 4,
        }
        for case, diff in case_difficulty.items():
            if case in parts:
                difficulty = max(difficulty, diff)
                break

        # Verb complexity
        if "verb" in parts:
            difficulty = max(difficulty, 3)
            if "past" in parts:
                difficulty = max(difficulty, 4)
            if "subjunctive" in parts or "conditional" in parts:
                difficulty = max(difficulty, 7)
            if "passive" in parts:
                difficulty = max(difficulty, 6)

        # Plural usually harder
        if "plural" in parts:
            difficulty = min(difficulty + 1, 10)

        return difficulty

    async def _create_external_mapping(
        self,
        session: AsyncSession,
        source_name: str,
        external_id: str,
        entity_type: str,
        internal_id: UUID,
        checksum: str | None = None,
    ) -> None:
        """Create mapping from external ID to internal ID."""
        mapping = ExternalIdMapping(
            source_name=source_name,
            external_id=external_id,
            entity_type=entity_type,
            internal_id=internal_id,
            checksum=checksum,
        )
        session.add(mapping)

    async def _get_existing_mapping(
        self,
        session: AsyncSession,
        source_name: str,
        external_id: str,
        entity_type: str,
    ) -> UUID | None:
        """Get existing internal ID for an external ID."""
        result = await session.execute(
            select(ExternalIdMapping.internal_id).where(
                ExternalIdMapping.source_name == source_name,
                ExternalIdMapping.external_id == external_id,
                ExternalIdMapping.entity_type == entity_type,
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def ingest_ud_corpus(
        self,
        conllu_path: Path | str,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> IngestionStats:
        """Ingest sentences and patterns from Universal Dependencies corpus."""
        stats = IngestionStats()
        parser = CoNLLUParser()
        source_name = "universal_dependencies"

        # First pass: collect all sentences for complexity calibration
        all_sentences = list(parser.parse_file(conllu_path))
        total = len(all_sentences)
        self._scorer = ComplexityScorer.from_corpus(all_sentences)

        async with get_db_session() as session:
            # Create or update ingestion record
            record = IngestionRecord(
                source_name=source_name,
                language=self.language,
                file_path=str(conllu_path),
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[tuple[UDSentence, int]] = []

                for idx, ud_sentence in enumerate(all_sentences):
                    batch.append((ud_sentence, idx))

                    if len(batch) >= self.batch_size:
                        await self._process_ud_batch(session, batch, source_name, stats)
                        batch = []

                        if progress_callback:
                            await progress_callback(stats.records_processed, total)

                # Process remaining
                if batch:
                    await self._process_ud_batch(session, batch, source_name, stats)

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

    async def _process_ud_batch(
        self,
        session: AsyncSession,
        batch: list[tuple[UDSentence, int]],
        source_name: str,
        stats: IngestionStats,
    ) -> None:
        """Process a batch of UD sentences."""
        for ud_sentence, _ in batch:
            stats.records_processed += 1

            try:
                # Check for existing
                existing_id = await self._get_existing_mapping(
                    session, source_name, ud_sentence.sent_id, "sentence"
                )
                if existing_id:
                    stats.records_skipped += 1
                    continue

                # Calculate complexity
                complexity = self._scorer.score(ud_sentence) if self._scorer else 5

                # Create sentence
                sentence = Sentence(
                    text=ud_sentence.text,
                    language=self.language,
                    complexity_score=complexity,
                    source=source_name,
                    extra_data={
                        "sent_id": ud_sentence.sent_id,
                        "metadata": ud_sentence.metadata,
                    },
                )
                session.add(sentence)
                await session.flush()

                # Create external mapping
                await self._create_external_mapping(
                    session, source_name, ud_sentence.sent_id, "sentence", sentence.id
                )

                # Extract and link patterns
                for pattern_key, position in ud_sentence.get_pattern_positions():
                    # Parse features from pattern key
                    parts = pattern_key.split("_")
                    features = {"raw_key": pattern_key}

                    if len(parts) >= 2:
                        features["upos"] = parts[0]
                    if len(parts) >= 3:
                        for part in parts[1:]:
                            if part in ("nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"):
                                features["case"] = part
                            elif part in ("singular", "plural"):
                                features["number"] = part
                            elif part in ("masculine", "feminine", "neuter"):
                                features["gender"] = part
                            elif part in ("present", "past", "future"):
                                features["tense"] = part

                    pattern_id = await self._get_or_create_pattern(session, pattern_key, features)

                    # Create sentence-pattern link
                    link = SentencePattern(
                        sentence_id=sentence.id,
                        pattern_id=pattern_id,
                        position=position,
                    )
                    session.add(link)

                stats.records_created += 1

            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Sentence {ud_sentence.sent_id}: {e}")

    async def ingest_wiktionary(
        self,
        dump_path: Path | str,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> IngestionStats:
        """Ingest lemmas and inflections from Wiktionary dump."""
        stats = IngestionStats()
        parser = WiktionaryParser()
        source_name = "wiktionary"

        async with get_db_session() as session:
            record = IngestionRecord(
                source_name=source_name,
                language=self.language,
                file_path=str(dump_path),
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[WiktionaryEntry] = []

                for entry in parser.parse_dump(dump_path):
                    if entry.language != self.language:
                        continue

                    batch.append(entry)

                    if len(batch) >= self.batch_size:
                        await self._process_wiktionary_batch(session, batch, source_name, stats)
                        batch = []

                        if progress_callback:
                            await progress_callback(stats.records_processed, -1)

                if batch:
                    await self._process_wiktionary_batch(session, batch, source_name, stats)

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

    async def _process_wiktionary_batch(
        self,
        session: AsyncSession,
        batch: list[WiktionaryEntry],
        source_name: str,
        stats: IngestionStats,
    ) -> None:
        """Process a batch of Wiktionary entries."""
        for entry in batch:
            stats.records_processed += 1

            try:
                external_id = f"{entry.title}:{entry.pos}"
                existing_id = await self._get_existing_mapping(
                    session, source_name, external_id, "lemma"
                )
                if existing_id:
                    stats.records_skipped += 1
                    continue

                # Create lemma
                lemma = Lemma(
                    word=entry.title,
                    language=self.language,
                    part_of_speech=entry.pos,
                    gender=entry.gender,
                    aspect=entry.aspect,
                    declension_class=entry.declension_class,
                    conjugation_class=entry.conjugation_class,
                    definition="; ".join(entry.definitions) if entry.definitions else None,
                    features={
                        "synonyms": entry.synonyms,
                        "antonyms": entry.antonyms,
                        "pronunciation": entry.pronunciation,
                    },
                )
                session.add(lemma)
                await session.flush()

                await self._create_external_mapping(
                    session, source_name, external_id, "lemma", lemma.id
                )

                # Create inflections
                for infl in entry.inflections:
                    inflection = Inflection(
                        lemma_id=lemma.id,
                        form=infl.form,
                        case=infl.case,
                        number=infl.number,
                        person=infl.person,
                        tense=infl.tense,
                        gender=infl.gender,
                        features={
                            "mood": infl.mood,
                            "aspect": infl.aspect,
                        },
                    )
                    session.add(inflection)

                # Create etymology if available
                if entry.etymology:
                    # First create/get the origin node
                    if entry.etymology.origin_word:
                        origin_node = EtymologyNode(
                            word=entry.etymology.origin_word,
                            language=entry.etymology.origin_language or "unknown",
                            meaning=None,
                            is_reconstructed="Y" if entry.etymology.origin_word.startswith("*") else "N",
                        )
                        session.add(origin_node)
                        await session.flush()

                        # Create current word node
                        current_node = EtymologyNode(
                            word=entry.title,
                            language=self.language,
                            part_of_speech=entry.pos,
                            meaning=entry.definitions[0] if entry.definitions else None,
                        )
                        session.add(current_node)
                        await session.flush()

                        # Create relation
                        relation = EtymologyRelation(
                            source_id=origin_node.id,
                            target_id=current_node.id,
                            relation_type=entry.etymology.relation_type,
                        )
                        session.add(relation)

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
        source_name = "tatoeba"

        async with get_db_session() as session:
            record = IngestionRecord(
                source_name=source_name,
                language=self.language,
                file_path=str(sentences_path),
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(record)
            await session.flush()

            try:
                batch: list[SentencePair] = []

                pairs = TatoebaParser.parse_pairs_file(
                    sentences_path, links_path, self.language, target_lang, limit
                )

                for pair in pairs:
                    batch.append(pair)

                    if len(batch) >= self.batch_size:
                        await self._process_tatoeba_batch(session, batch, source_name, stats)
                        batch = []

                        if progress_callback:
                            await progress_callback(stats.records_processed, limit or -1)

                if batch:
                    await self._process_tatoeba_batch(session, batch, source_name, stats)

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

    async def _process_tatoeba_batch(
        self,
        session: AsyncSession,
        batch: list[SentencePair],
        source_name: str,
        stats: IngestionStats,
    ) -> None:
        """Process a batch of Tatoeba sentence pairs."""
        for pair in batch:
            stats.records_processed += 1

            try:
                external_id = str(pair.source.id)

                # Check if we have this sentence already
                existing_id = await self._get_existing_mapping(
                    session, source_name, external_id, "sentence"
                )

                if existing_id:
                    # Update with translation
                    result = await session.execute(
                        select(Sentence).where(Sentence.id == existing_id)
                    )
                    sentence = result.scalar_one_or_none()
                    if sentence and not sentence.translation:
                        sentence.translation = pair.target.text
                        stats.records_updated += 1
                    else:
                        stats.records_skipped += 1
                    continue

                # Also check if we imported this from UD
                result = await session.execute(
                    select(Sentence).where(
                        Sentence.text == pair.source.text,
                        Sentence.language == self.language,
                    )
                )
                sentence = result.scalar_one_or_none()

                if sentence:
                    # Update existing sentence with translation
                    if not sentence.translation:
                        sentence.translation = pair.target.text
                        stats.records_updated += 1
                    else:
                        stats.records_skipped += 1
                else:
                    # Create new sentence
                    sentence = Sentence(
                        text=pair.source.text,
                        language=self.language,
                        translation=pair.target.text,
                        complexity_score=5,  # Default, will be updated later
                        source=source_name,
                        extra_data={
                            "tatoeba_id": pair.source.id,
                            "translation_id": pair.target.id,
                        },
                    )
                    session.add(sentence)
                    await session.flush()

                    await self._create_external_mapping(
                        session, source_name, external_id, "sentence", sentence.id
                    )
                    stats.records_created += 1

            except Exception as e:
                stats.records_failed += 1
                stats.errors.append(f"Pair {pair.source.id}: {e}")

