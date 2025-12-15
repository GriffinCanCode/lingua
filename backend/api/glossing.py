from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.glossing import GlossedText, Morpheme
from engines.glossing import GlossingEngine

router = APIRouter()


class MorphemeResponse(BaseModel):
    word_index: int
    morpheme_index: int
    surface_form: str
    gloss: str
    morpheme_type: Optional[str]
    lemma: Optional[str]

    class Config:
        from_attributes = True


class WordGloss(BaseModel):
    word: str
    morphemes: list[MorphemeResponse]
    full_gloss: str  # Combined gloss for the word


class InterlinearLine(BaseModel):
    original: list[str]
    morphemes: list[str]
    glosses: list[str]
    translation: Optional[str]


class GlossedTextCreate(BaseModel):
    title: Optional[str] = None
    original_text: str
    language: str = "ru"
    translation: Optional[str] = None
    source: Optional[str] = None
    difficulty: int = 1


class GlossedTextResponse(BaseModel):
    id: UUID
    title: Optional[str]
    original_text: str
    language: str
    translation: Optional[str]
    difficulty: int

    class Config:
        from_attributes = True


class FullGlossedText(BaseModel):
    text: GlossedTextResponse
    lines: list[InterlinearLine]


@router.post("/gloss", response_model=list[WordGloss])
async def gloss_text(
    text: str,
    language: str = Query("ru"),
):
    """Generate Leipzig-style glosses for text"""
    engine = GlossingEngine(language)
    glossed = engine.gloss_text(text)
    
    return [
        WordGloss(
            word=g["word"],
            morphemes=[MorphemeResponse(**m) for m in g["morphemes"]],
            full_gloss=g["full_gloss"],
        )
        for g in glossed
    ]


@router.get("/interlinear", response_model=InterlinearLine)
async def get_interlinear(
    text: str,
    language: str = Query("ru"),
    include_translation: bool = Query(True),
):
    """Get interlinear gloss format for a sentence"""
    engine = GlossingEngine(language)
    interlinear = engine.get_interlinear(text, include_translation=include_translation)
    return InterlinearLine(**interlinear)


@router.post("/texts", response_model=GlossedTextResponse)
async def create_glossed_text(
    text_data: GlossedTextCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new glossed text entry"""
    text = GlossedText(**text_data.model_dump())
    db.add(text)
    await db.commit()
    await db.refresh(text)
    
    # Auto-generate morpheme annotations
    engine = GlossingEngine(text_data.language)
    glossed = engine.gloss_text(text_data.original_text)
    
    for word_data in glossed:
        for m in word_data["morphemes"]:
            morpheme = Morpheme(
                text_id=text.id,
                word_index=m["word_index"],
                morpheme_index=m["morpheme_index"],
                surface_form=m["surface_form"],
                gloss=m["gloss"],
                morpheme_type=m.get("morpheme_type"),
                lemma=m.get("lemma"),
            )
            db.add(morpheme)
    
    await db.commit()
    return text


@router.get("/texts/{text_id}", response_model=FullGlossedText)
async def get_glossed_text(text_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a glossed text with all annotations"""
    result = await db.execute(select(GlossedText).where(GlossedText.id == text_id))
    text = result.scalar_one_or_none()
    if not text:
        raise HTTPException(status_code=404, detail="Text not found")
    
    # Get morphemes
    result = await db.execute(
        select(Morpheme)
        .where(Morpheme.text_id == text_id)
        .order_by(Morpheme.word_index, Morpheme.morpheme_index)
    )
    morphemes = result.scalars().all()
    
    # Group by sentence/line
    engine = GlossingEngine(text.language)
    lines = engine.format_as_interlinear(text.original_text, morphemes, text.translation)
    
    return FullGlossedText(
        text=GlossedTextResponse.model_validate(text),
        lines=[InterlinearLine(**line) for line in lines],
    )


@router.get("/texts", response_model=list[GlossedTextResponse])
async def list_glossed_texts(
    language: str = Query("ru"),
    difficulty_min: int = Query(1),
    difficulty_max: int = Query(10),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List available glossed texts"""
    result = await db.execute(
        select(GlossedText)
        .where(
            GlossedText.language == language,
            GlossedText.difficulty >= difficulty_min,
            GlossedText.difficulty <= difficulty_max,
        )
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/morpheme/{word}", response_model=list[MorphemeResponse])
async def analyze_morphemes(word: str, language: str = Query("ru")):
    """Get morpheme breakdown for a single word"""
    engine = GlossingEngine(language)
    morphemes = engine.segment_word(word)
    return [MorphemeResponse(**m) for m in morphemes]

