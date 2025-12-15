from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user_id
from models.production import ProductionPrompt, ProductionAttempt, ProductionFeedback
from engines.production import ProductionEngine

router = APIRouter()


class PromptCreate(BaseModel):
    prompt_type: str  # translation, fill_blank, free_production
    language: str = "ru"
    prompt_text: str
    expected_patterns: list[str] = []
    target_structures: list[dict] = []
    acceptable_answers: list[str] = []
    hints: list[str] = []
    difficulty: int = 1


class PromptResponse(BaseModel):
    id: UUID
    prompt_type: str
    prompt_text: str
    difficulty: int
    hints: list[str]

    class Config:
        from_attributes = True


class AttemptCreate(BaseModel):
    prompt_id: UUID
    user_response: str
    time_taken_seconds: Optional[int] = None


class ErrorDetail(BaseModel):
    error_type: str  # morphological, syntactic, semantic, phonetic
    description: str
    correction: str
    explanation: str
    severity: int  # 1-5


class AttemptFeedback(BaseModel):
    is_correct: str  # Y/N/P
    score: float
    errors: list[ErrorDetail]
    corrected_text: str
    suggestions: list[str]


class AttemptResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    user_response: str
    is_correct: str
    score: float
    feedback: AttemptFeedback

    class Config:
        from_attributes = True


@router.post("/prompts", response_model=PromptResponse)
async def create_prompt(prompt_data: PromptCreate, db: AsyncSession = Depends(get_db)):
    prompt = ProductionPrompt(**prompt_data.model_dump())
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductionPrompt).where(ProductionPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.get("/prompts", response_model=list[PromptResponse])
async def get_prompts(
    language: str = Query("ru"),
    prompt_type: Optional[str] = Query(None),
    difficulty_min: int = Query(1),
    difficulty_max: int = Query(10),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductionPrompt).where(
        ProductionPrompt.language == language,
        ProductionPrompt.difficulty >= difficulty_min,
        ProductionPrompt.difficulty <= difficulty_max,
    )
    if prompt_type:
        query = query.where(ProductionPrompt.prompt_type == prompt_type)
    query = query.limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/attempt", response_model=AttemptResponse)
async def submit_attempt(
    attempt_data: AttemptCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit a production attempt and get feedback"""
    # Get the prompt
    result = await db.execute(
        select(ProductionPrompt).where(ProductionPrompt.id == attempt_data.prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Analyze the response
    engine = ProductionEngine(prompt.language)
    analysis = engine.analyze_response(
        user_response=attempt_data.user_response,
        expected_patterns=prompt.expected_patterns,
        target_structures=prompt.target_structures,
        acceptable_answers=prompt.acceptable_answers,
    )
    
    # Determine correctness
    is_correct = "Y" if analysis["score"] >= 0.9 else ("P" if analysis["score"] >= 0.5 else "N")
    
    # Create attempt record
    attempt = ProductionAttempt(
        user_id=UUID(user_id),
        prompt_id=prompt.id,
        user_response=attempt_data.user_response,
        is_correct=is_correct,
        score=analysis["score"],
        time_taken_seconds=attempt_data.time_taken_seconds,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    
    # Create feedback records
    for error in analysis["errors"]:
        feedback = ProductionFeedback(
            attempt_id=attempt.id,
            error_type=error["error_type"],
            error_description=error["description"],
            correction=error["correction"],
            explanation=error["explanation"],
            severity=error["severity"],
        )
        db.add(feedback)
    await db.commit()
    
    return AttemptResponse(
        id=attempt.id,
        prompt_id=prompt.id,
        user_response=attempt_data.user_response,
        is_correct=is_correct,
        score=analysis["score"],
        feedback=AttemptFeedback(
            is_correct=is_correct,
            score=analysis["score"],
            errors=[ErrorDetail(**e) for e in analysis["errors"]],
            corrected_text=analysis["corrected_text"],
            suggestions=analysis["suggestions"],
        ),
    )


@router.post("/attempt-audio", response_model=AttemptResponse)
async def submit_audio_attempt(
    prompt_id: UUID,
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit an audio production attempt"""
    # This would integrate with speech-to-text and phonetic analysis
    # For now, return a placeholder
    raise HTTPException(status_code=501, detail="Audio production not yet implemented")


@router.get("/history", response_model=list[dict])
async def get_attempt_history(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get user's production attempt history"""
    result = await db.execute(
        select(ProductionAttempt, ProductionPrompt)
        .join(ProductionPrompt)
        .where(
            ProductionAttempt.user_id == UUID(user_id),
            ProductionPrompt.language == language,
        )
        .order_by(ProductionAttempt.created_at.desc())
        .limit(limit)
    )
    
    history = []
    for attempt, prompt in result.all():
        history.append({
            "attempt_id": str(attempt.id),
            "prompt_text": prompt.prompt_text,
            "user_response": attempt.user_response,
            "is_correct": attempt.is_correct,
            "score": attempt.score,
            "created_at": attempt.created_at.isoformat(),
        })
    
    return history


@router.get("/stats")
async def get_production_stats(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Get user's production statistics"""
    result = await db.execute(
        select(ProductionAttempt, ProductionPrompt)
        .join(ProductionPrompt)
        .where(
            ProductionAttempt.user_id == UUID(user_id),
            ProductionPrompt.language == language,
        )
    )
    
    attempts = result.all()
    total = len(attempts)
    if total == 0:
        return {
            "total_attempts": 0,
            "accuracy": 0,
            "average_score": 0,
            "by_type": {},
        }
    
    correct = sum(1 for a, _ in attempts if a.is_correct == "Y")
    partial = sum(1 for a, _ in attempts if a.is_correct == "P")
    avg_score = sum(a.score for a, _ in attempts) / total
    
    by_type = {}
    for attempt, prompt in attempts:
        if prompt.prompt_type not in by_type:
            by_type[prompt.prompt_type] = {"total": 0, "correct": 0}
        by_type[prompt.prompt_type]["total"] += 1
        if attempt.is_correct == "Y":
            by_type[prompt.prompt_type]["correct"] += 1
    
    return {
        "total_attempts": total,
        "correct": correct,
        "partial": partial,
        "accuracy": correct / total,
        "average_score": avg_score,
        "by_type": by_type,
    }

