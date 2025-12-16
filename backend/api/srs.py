"""SRS (Spaced Repetition System) API with Monadic Error Handling

Handles sentence management, review scheduling, mastery tracking,
and vocabulary state tracking using Result types for predictable error propagation.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, fetch_one, create_entity
from core.security import get_current_user_id
from core.errors import raise_result
from models.srs import Sentence, SyntacticPattern, SentencePattern, UserPatternMastery, Vocabulary, UserVocabMastery
from engines.srs import SRSEngine
from engines.tracking import WordTracker, VocabState

router = APIRouter()


class SentenceCreate(BaseModel):
    text: str
    language: str = "ru"
    translation: str | None = None
    complexity_score: int = 1
    source: str | None = None


class SentenceResponse(BaseModel):
    id: UUID
    text: str
    language: str
    translation: str | None
    complexity_score: int

    class Config:
        from_attributes = True


class PatternResponse(BaseModel):
    id: UUID
    pattern_type: str
    description: str | None
    difficulty: int
    features: dict

    class Config:
        from_attributes = True


class ReviewItem(BaseModel):
    sentence: SentenceResponse
    patterns: list[PatternResponse]
    due: bool


class ReviewResult(BaseModel):
    pattern_id: UUID
    quality: int  # 0-5 SM-2 quality rating


class MasteryStats(BaseModel):
    pattern_id: UUID
    pattern_type: str
    mastery_level: float  # 0-1
    next_review: datetime | None
    total_reviews: int


@router.post("/sentences", response_model=SentenceResponse)
async def create_sentence(sentence_data: SentenceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new sentence for SRS."""
    sentence = Sentence(**sentence_data.model_dump())
    result = await create_entity(db, sentence)
    raise_result(result)
    return result.unwrap()


@router.get("/sentences/{sentence_id}", response_model=SentenceResponse)
async def get_sentence(sentence_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a sentence by ID."""
    result = await fetch_one(db, Sentence, sentence_id, "Sentence")
    raise_result(result)
    return result.unwrap()


@router.get("/sentences", response_model=list[SentenceResponse])
async def search_sentences(
    language: str = Query("ru"),
    pattern_type: str | None = Query(None),
    complexity_min: int = Query(1),
    complexity_max: int = Query(10),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search sentences with filters."""
    query = select(Sentence).where(
        Sentence.language == language,
        Sentence.complexity_score >= complexity_min,
        Sentence.complexity_score <= complexity_max,
    )
    
    if pattern_type:
        query = query.join(SentencePattern).join(SyntacticPattern).where(
            SyntacticPattern.pattern_type == pattern_type
        )
    
    result = await db.execute(query.limit(limit))
    return result.scalars().all()


@router.get("/patterns", response_model=list[PatternResponse])
async def get_patterns(language: str = Query("ru"), db: AsyncSession = Depends(get_db)):
    """Get all syntactic patterns for a language."""
    result = await db.execute(
        select(SyntacticPattern).where(SyntacticPattern.language == language)
    )
    return result.scalars().all()


@router.get("/due", response_model=list[ReviewItem])
async def get_due_reviews(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get sentences due for review based on user's pattern mastery."""
    # Get user's due pattern mastery records
    result = await db.execute(
        select(UserPatternMastery).where(
            UserPatternMastery.user_id == UUID(user_id),
            UserPatternMastery.next_review <= datetime.utcnow(),
        )
    )
    due_mastery = result.scalars().all()
    due_pattern_ids = {m.pattern_id for m in due_mastery}
    
    # Find sentences containing due patterns
    if due_pattern_ids:
        result = await db.execute(
            select(Sentence)
            .join(SentencePattern)
            .where(
                Sentence.language == language,
                SentencePattern.pattern_id.in_(due_pattern_ids),
            )
            .limit(limit)
        )
        sentences = result.scalars().unique().all()
    else:
        # No due patterns - get new sentences to introduce
        result = await db.execute(
            select(Sentence)
            .where(Sentence.language == language)
            .order_by(Sentence.complexity_score)
            .limit(limit)
        )
        sentences = result.scalars().all()
    
    # Build review items with patterns
    items = []
    for s in sentences:
        result = await db.execute(
            select(SyntacticPattern)
            .join(SentencePattern)
            .where(SentencePattern.sentence_id == s.id)
        )
        patterns = result.scalars().all()
        
        items.append(ReviewItem(
            sentence=SentenceResponse.model_validate(s),
            patterns=[PatternResponse.model_validate(p) for p in patterns],
            due=any(p.id in due_pattern_ids for p in patterns),
        ))
    
    return items


@router.post("/review")
async def submit_review(
    results: list[ReviewResult],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit review results and update SRS scheduling."""
    engine = SRSEngine()
    
    for result in results:
        # Get or create mastery record
        query = select(UserPatternMastery).where(
            UserPatternMastery.user_id == UUID(user_id),
            UserPatternMastery.pattern_id == result.pattern_id,
        )
        res = await db.execute(query)
        mastery = res.scalar_one_or_none()
        
        if not mastery:
            mastery = UserPatternMastery(
                user_id=UUID(user_id),
                pattern_id=result.pattern_id,
            )
            db.add(mastery)
        
        # Calculate new SRS values
        new_values = engine.calculate_sm2(
            quality=result.quality,
            repetitions=mastery.repetitions,
            ease_factor=mastery.ease_factor,
            interval=mastery.interval,
        )
        
        mastery.ease_factor = new_values["ease_factor"]
        mastery.interval = new_values["interval"]
        mastery.repetitions = new_values["repetitions"]
        mastery.next_review = new_values["next_review"]
        mastery.last_review = datetime.utcnow()
        mastery.total_reviews += 1
        if result.quality >= 3:
            mastery.correct_reviews += 1
    
    await db.commit()
    return {"status": "success", "reviewed": len(results)}


@router.get("/mastery", response_model=list[MasteryStats])
async def get_mastery_stats(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Get user's mastery statistics for all patterns."""
    result = await db.execute(
        select(UserPatternMastery, SyntacticPattern)
        .join(SyntacticPattern)
        .where(
            UserPatternMastery.user_id == UUID(user_id),
            SyntacticPattern.language == language,
        )
    )
    
    return [
        MasteryStats(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            mastery_level=mastery.correct_reviews / max(mastery.total_reviews, 1),
            next_review=mastery.next_review,
            total_reviews=mastery.total_reviews,
        )
        for mastery, pattern in result.all()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# VOCABULARY TRACKING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class VocabResponse(BaseModel):
    id: str
    word: str
    translation: str
    pos: str | None
    gender: str | None

    class Config:
        from_attributes = True


class VocabStateResponse(BaseModel):
    vocab_id: str
    word: str
    translation: str
    state: str
    exposure_count: int
    correct_count: int
    pos: str | None = None
    gender: str | None = None


class VocabPoolResponse(BaseModel):
    new: list[VocabStateResponse]
    practice: list[VocabStateResponse]
    review: list[VocabStateResponse]


class VocabExposureRequest(BaseModel):
    vocab_id: str
    exposure_type: Literal["intro", "definition", "exercise", "review"]
    correct: bool | None = None


class VocabExposureBatchRequest(BaseModel):
    exposures: list[VocabExposureRequest]


@router.get("/vocab", response_model=list[VocabResponse])
async def list_vocabulary(
    language: str = Query("ru"),
    pos: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List vocabulary items with optional filters."""
    query = select(Vocabulary).where(Vocabulary.language == language)
    if pos:
        query = query.where(Vocabulary.pos == pos)
    result = await db.execute(query.limit(limit))
    return result.scalars().all()


@router.get("/vocab/states", response_model=list[VocabStateResponse])
async def get_vocab_states(
    vocab_ids: str = Query(..., description="Comma-separated vocab IDs"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get user's mastery states for vocabulary items."""
    ids = [v.strip() for v in vocab_ids.split(",") if v.strip()]
    tracker = WordTracker(db)
    states = await tracker.get_vocab_states(UUID(user_id), ids)
    return [
        VocabStateResponse(
            vocab_id=ws.vocab_id,
            word=ws.word,
            translation=ws.translation,
            state=ws.state,
            exposure_count=ws.exposure_count,
            correct_count=ws.correct_count,
            pos=ws.pos,
            gender=ws.gender,
        )
        for ws in states.values()
    ]


@router.get("/vocab/pool", response_model=VocabPoolResponse)
async def get_vocab_pool(
    lesson_vocab: str = Query(..., description="Comma-separated lesson vocab IDs"),
    review_vocab: str | None = Query(None, description="Comma-separated review vocab IDs"),
    max_new: int = Query(5, le=10),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get vocabulary pool for a lesson session, categorized by learning state."""
    lesson_ids = [v.strip() for v in lesson_vocab.split(",") if v.strip()]
    review_ids = [v.strip() for v in review_vocab.split(",")] if review_vocab else []

    tracker = WordTracker(db)
    pool = await tracker.get_vocab_pool(UUID(user_id), lesson_ids, review_ids, max_new)

    def to_response(ws):
        return VocabStateResponse(
            vocab_id=ws.vocab_id, word=ws.word, translation=ws.translation,
            state=ws.state, exposure_count=ws.exposure_count, correct_count=ws.correct_count,
            pos=ws.pos, gender=ws.gender,
        )

    return VocabPoolResponse(
        new=[to_response(ws) for ws in pool.new],
        practice=[to_response(ws) for ws in pool.practice],
        review=[to_response(ws) for ws in pool.review],
    )


@router.post("/vocab/exposure")
async def record_vocab_exposure(
    request: VocabExposureRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Record a vocabulary exposure event and update state."""
    tracker = WordTracker(db)
    new_state = await tracker.record_exposure(
        UUID(user_id), request.vocab_id, request.exposure_type, request.correct
    )
    await db.commit()
    return {"vocab_id": request.vocab_id, "new_state": new_state}


@router.post("/vocab/exposure/batch")
async def record_vocab_exposure_batch(
    request: VocabExposureBatchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Record multiple vocabulary exposure events."""
    tracker = WordTracker(db)
    results = []
    for exp in request.exposures:
        new_state = await tracker.record_exposure(
            UUID(user_id), exp.vocab_id, exp.exposure_type, exp.correct
        )
        results.append({"vocab_id": exp.vocab_id, "new_state": new_state})
    await db.commit()
    return {"updated": results}


@router.get("/vocab/due", response_model=list[VocabStateResponse])
async def get_due_vocab_reviews(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get vocabulary items due for SRS review."""
    tracker = WordTracker(db)
    due = await tracker.get_due_reviews(UUID(user_id), limit)
    return [
        VocabStateResponse(
            vocab_id=ws.vocab_id, word=ws.word, translation=ws.translation,
            state=ws.state, exposure_count=ws.exposure_count, correct_count=ws.correct_count,
            pos=ws.pos, gender=ws.gender,
        )
        for ws in due
    ]
