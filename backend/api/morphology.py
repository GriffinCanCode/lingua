"""Morphology API with Monadic Error Handling

Handles morphological analysis, inflection generation, and paradigm lookup
using Result types for predictable error propagation.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, fetch_one, create_entity
from core.errors import raise_result
from models.morphology import Lemma, MorphologicalRule, Inflection
from engines.morphology import MorphologyEngine

router = APIRouter()


class LemmaCreate(BaseModel):
    word: str
    language: str = "ru"
    part_of_speech: str
    gender: str | None = None
    aspect: str | None = None
    declension_class: str | None = None
    conjugation_class: str | None = None
    definition: str | None = None


class LemmaResponse(BaseModel):
    id: UUID
    word: str
    language: str
    part_of_speech: str
    gender: str | None
    definition: str | None

    class Config:
        from_attributes = True


class InflectionResponse(BaseModel):
    form: str
    case: str | None = None
    number: str | None = None
    person: str | None = None
    tense: str | None = None
    gender: str | None = None


class ParadigmResponse(BaseModel):
    lemma: LemmaResponse
    inflections: list[InflectionResponse]


class AnalysisResponse(BaseModel):
    word: str
    lemma: str
    part_of_speech: str
    features: dict


@router.post("/lemmas", response_model=LemmaResponse)
async def create_lemma(lemma_data: LemmaCreate, db: AsyncSession = Depends(get_db)):
    """Create a new lemma entry."""
    lemma = Lemma(**lemma_data.model_dump())
    result = await create_entity(db, lemma)
    raise_result(result)
    return result.unwrap()


@router.get("/lemmas/{lemma_id}", response_model=LemmaResponse)
async def get_lemma(lemma_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a lemma by ID."""
    result = await fetch_one(db, Lemma, lemma_id, "Lemma")
    raise_result(result)
    return result.unwrap()


@router.get("/lemmas", response_model=list[LemmaResponse])
async def search_lemmas(
    word: str | None = Query(None),
    language: str = Query("ru"),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search lemmas with filters."""
    query = select(Lemma).where(Lemma.language == language)
    if word:
        query = query.where(Lemma.word.ilike(f"%{word}%"))
    result = await db.execute(query.limit(limit))
    return result.scalars().all()


@router.get("/analyze/{word}", response_model=list[AnalysisResponse])
async def analyze_word(word: str, language: str = Query("ru")):
    """Analyze a word and return morphological features."""
    engine = MorphologyEngine(language)
    analyses = engine.analyze(word)
    return [
        AnalysisResponse(
            word=word,
            lemma=a["lemma"],
            part_of_speech=a["pos"],
            features=a["features"],
        )
        for a in analyses
    ]


@router.get("/generate/{lemma}", response_model=list[InflectionResponse])
async def generate_forms(
    lemma: str,
    language: str = Query("ru"),
    case: str | None = Query(None),
    number: str | None = Query(None),
):
    """Generate inflected forms from a lemma."""
    engine = MorphologyEngine(language)
    forms = engine.generate(lemma, case=case, number=number)
    return [InflectionResponse(**f) for f in forms]


@router.get("/paradigm/{lemma}", response_model=ParadigmResponse)
async def get_paradigm(lemma: str, language: str = Query("ru"), db: AsyncSession = Depends(get_db)):
    """Get complete paradigm (all forms) for a lemma."""
    engine = MorphologyEngine(language)
    
    # Check if lemma exists in DB
    result = await db.execute(
        select(Lemma).where(Lemma.word == lemma, Lemma.language == language)
    )
    db_lemma = result.scalar_one_or_none()
    
    # Generate all forms
    all_forms = engine.get_paradigm(lemma)
    
    lemma_response = LemmaResponse(
        id=db_lemma.id if db_lemma else UUID("00000000-0000-0000-0000-000000000000"),
        word=lemma,
        language=language,
        part_of_speech=all_forms[0]["pos"] if all_forms else "unknown",
        gender=all_forms[0].get("gender") if all_forms else None,
        definition=db_lemma.definition if db_lemma else None,
    )
    
    return ParadigmResponse(
        lemma=lemma_response,
        inflections=[InflectionResponse(**f) for f in all_forms],
    )


@router.get("/rules", response_model=list[dict])
async def get_rules(
    language: str = Query("ru"),
    rule_type: str | None = Query(None),
    pattern_class: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get morphological rules for teaching."""
    query = select(MorphologicalRule).where(MorphologicalRule.language == language)
    if rule_type:
        query = query.where(MorphologicalRule.rule_type == rule_type)
    if pattern_class:
        query = query.where(MorphologicalRule.pattern_class == pattern_class)
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "rule_type": r.rule_type,
            "pattern_class": r.pattern_class,
            "case": r.case,
            "number": r.number,
            "ending": r.ending,
            "description": r.description,
            "examples": r.examples,
        }
        for r in rules
    ]
