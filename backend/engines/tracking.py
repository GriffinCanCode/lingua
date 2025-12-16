"""Word Tracking Engine

Tracks vocabulary exposure states and determines exercise eligibility.
States: unseen → introduced → defined → practiced → mastered
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import engine_logger
from models.srs import Vocabulary, UserVocabMastery

log = engine_logger()

VocabState = Literal["unseen", "introduced", "defined", "practiced", "mastered"]
ExposureType = Literal["intro", "definition", "exercise", "review"]


@dataclass(slots=True)
class WordState:
    """Current state of a vocabulary item for a user."""
    vocab_id: str
    word: str
    translation: str
    state: VocabState
    exposure_count: int
    correct_count: int
    pos: str | None = None
    gender: str | None = None


@dataclass(slots=True)
class VocabPool:
    """Vocabulary categorized by learning state."""
    new: list[WordState]       # To introduce this session
    practice: list[WordState]  # Actively learning
    review: list[WordState]    # For spaced repetition


# Thresholds for state transitions
TRANSITION_THRESHOLDS = {
    "introduced_to_defined": 1,    # See definition once
    "defined_to_practiced": 3,     # 3 correct exercises
    "practiced_to_mastered": 10,   # 10 total correct with good SRS intervals
}

# Exercise types appropriate for each state
EXERCISE_TYPES_BY_STATE: dict[VocabState, list[str]] = {
    "unseen": ["word_intro"],
    "introduced": ["word_intro", "multiple_choice"],
    "defined": ["word_bank", "multiple_choice", "matching"],
    "practiced": ["word_bank", "typing", "fill_blank", "pattern_fill"],
    "mastered": ["typing", "pattern_apply", "paradigm_complete"],
}


class WordTracker:
    """Tracks vocabulary exposure and manages state transitions."""

    __slots__ = ("_db",)

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_vocab_states(self, user_id: UUID, vocab_ids: list[str]) -> dict[str, WordState]:
        """Get current states for vocabulary items."""
        # Fetch vocab items
        vocab_result = await self._db.execute(
            select(Vocabulary).where(Vocabulary.id.in_(vocab_ids))
        )
        vocab_items = {v.id: v for v in vocab_result.scalars().all()}

        # Fetch user mastery
        mastery_result = await self._db.execute(
            select(UserVocabMastery).where(
                UserVocabMastery.user_id == user_id,
                UserVocabMastery.vocab_id.in_(vocab_ids)
            )
        )
        mastery_map = {m.vocab_id: m for m in mastery_result.scalars().all()}

        states = {}
        for vid in vocab_ids:
            vocab = vocab_items.get(vid)
            if not vocab:
                continue

            mastery = mastery_map.get(vid)
            states[vid] = WordState(
                vocab_id=vid,
                word=vocab.word,
                translation=vocab.translation,
                state=mastery.state if mastery else "unseen",
                exposure_count=mastery.exposure_count if mastery else 0,
                correct_count=mastery.correct_count if mastery else 0,
                pos=vocab.pos,
                gender=vocab.gender,
            )

        return states

    async def get_vocab_pool(
        self,
        user_id: UUID,
        lesson_vocab_ids: list[str],
        review_vocab_ids: list[str] | None = None,
        max_new: int = 5,
    ) -> VocabPool:
        """Get vocabulary categorized for a lesson session."""
        all_ids = list(set(lesson_vocab_ids + (review_vocab_ids or [])))
        states = await self.get_vocab_states(user_id, all_ids)

        new, practice, review = [], [], []

        for vid in lesson_vocab_ids:
            ws = states.get(vid)
            if not ws:
                continue
            if ws.state == "unseen":
                new.append(ws)
            elif ws.state in ("introduced", "defined"):
                practice.append(ws)
            else:
                review.append(ws)

        # Add review vocab
        for vid in (review_vocab_ids or []):
            ws = states.get(vid)
            if ws and ws not in review:
                review.append(ws)

        # Limit new words per session
        new = new[:max_new]

        log.debug("vocab_pool_built", new=len(new), practice=len(practice), review=len(review))
        return VocabPool(new=new, practice=practice, review=review)

    async def record_exposure(
        self,
        user_id: UUID,
        vocab_id: str,
        exposure_type: ExposureType,
        correct: bool | None = None,
    ) -> VocabState:
        """Record vocabulary exposure and update state."""
        # Get or create mastery record
        result = await self._db.execute(
            select(UserVocabMastery).where(
                UserVocabMastery.user_id == user_id,
                UserVocabMastery.vocab_id == vocab_id
            )
        )
        mastery = result.scalar_one_or_none()

        if not mastery:
            mastery = UserVocabMastery(
                user_id=user_id,
                vocab_id=vocab_id,
                state="unseen",
                exposure_count=0,
                correct_count=0,
            )
            self._db.add(mastery)

        # Update counts
        mastery.exposure_count += 1
        if correct is True:
            mastery.correct_count += 1
        mastery.last_review = datetime.utcnow()
        mastery.updated_at = datetime.utcnow()

        # State transitions
        new_state = self._calculate_transition(mastery, exposure_type, correct)
        if new_state != mastery.state:
            log.info("vocab_state_transition", vocab_id=vocab_id, old=mastery.state, new=new_state)
            mastery.state = new_state

            # Set SRS schedule when entering mastered
            if new_state == "mastered":
                mastery.interval = 1
                mastery.next_review = datetime.utcnow() + timedelta(days=1)

        await self._db.flush()
        return new_state

    def _calculate_transition(
        self,
        mastery: UserVocabMastery,
        exposure_type: ExposureType,
        correct: bool | None,
    ) -> VocabState:
        """Determine if state should transition."""
        state = mastery.state

        if state == "unseen" and exposure_type == "intro":
            return "introduced"

        if state == "introduced" and exposure_type == "definition":
            return "defined"

        if state == "defined" and correct is True:
            if mastery.correct_count >= TRANSITION_THRESHOLDS["defined_to_practiced"]:
                return "practiced"

        if state == "practiced" and correct is True:
            if mastery.correct_count >= TRANSITION_THRESHOLDS["practiced_to_mastered"]:
                return "mastered"

        return state

    async def get_due_reviews(self, user_id: UUID, limit: int = 20) -> list[WordState]:
        """Get vocabulary items due for SRS review."""
        now = datetime.utcnow()
        result = await self._db.execute(
            select(UserVocabMastery, Vocabulary)
            .join(Vocabulary, UserVocabMastery.vocab_id == Vocabulary.id)
            .where(
                UserVocabMastery.user_id == user_id,
                UserVocabMastery.state == "mastered",
                UserVocabMastery.next_review <= now
            )
            .limit(limit)
        )

        due = []
        for mastery, vocab in result.all():
            due.append(WordState(
                vocab_id=vocab.id,
                word=vocab.word,
                translation=vocab.translation,
                state=mastery.state,
                exposure_count=mastery.exposure_count,
                correct_count=mastery.correct_count,
                pos=vocab.pos,
                gender=vocab.gender,
            ))

        return due

    @staticmethod
    def get_eligible_exercise_types(states: list[WordState]) -> list[str]:
        """Get exercise types appropriate for the given word states."""
        eligible = set()
        for ws in states:
            eligible.update(EXERCISE_TYPES_BY_STATE.get(ws.state, []))
        return list(eligible)


async def sync_vocab_from_yaml(db: AsyncSession, vocab_data: list[dict], language: str = "ru") -> int:
    """Sync vocabulary from YAML data to database."""
    count = 0
    for item in vocab_data:
        vocab_id = item.get("id")
        if not vocab_id:
            continue

        result = await db.execute(select(Vocabulary).where(Vocabulary.id == vocab_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.word = item.get("word", existing.word)
            existing.translation = item.get("translation", existing.translation)
            existing.pos = item.get("pos", existing.pos)
            existing.gender = item.get("gender", existing.gender)
            existing.semantic = item.get("semantic", existing.semantic)
            existing.frequency = item.get("frequency", existing.frequency)
            existing.difficulty = item.get("difficulty", existing.difficulty)
            existing.audio = item.get("audio", existing.audio)
            existing.notes = item.get("notes", existing.notes)
        else:
            db.add(Vocabulary(
                id=vocab_id,
                word=item.get("word", ""),
                translation=item.get("translation", ""),
                language=language,
                pos=item.get("pos"),
                gender=item.get("gender"),
                semantic=item.get("semantic", []),
                frequency=item.get("frequency", 1),
                difficulty=item.get("difficulty", 1),
                audio=item.get("audio"),
                notes=item.get("notes"),
            ))
            count += 1

    await db.flush()
    log.info("vocab_synced", new_items=count, total=len(vocab_data))
    return count
