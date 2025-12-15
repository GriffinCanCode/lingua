from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.morphology import Lemma, MorphologicalRule, Inflection
from engines.morphology import MorphologyEngine

router = APIRouter()


class LemmaCreate(BaseModel):
    word: str
    language: str = "ru"
    part_of_speech: str
    gender: Optional[str] = None
    aspect: Optional[str] = None
    declension_class: Optional[str] = None
    conjugation_class: Optional[str] = None
    definition: Optional[str] = None


class LemmaResponse(BaseModel):
    id: UUID
    word: str
    language: str
    part_of_speech: str
    gender: Optional[str]
    definition: Optional[str]

    class Config:
        from_attributes = True


class InflectionResponse(BaseModel):
    form: str
    case: Optional[str]
    number: Optional[str]
    person: Optional[str]
    tense: Optional[str]
    gender: Optional[str]


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
    lemma = Lemma(**lemma_data.model_dump())
    db.add(lemma)
    await db.commit()
    await db.refresh(lemma)
    return lemma


@router.get("/lemmas/{lemma_id}", response_model=LemmaResponse)
async def get_lemma(lemma_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lemma).where(Lemma.id == lemma_id))
    lemma = result.scalar_one_or_none()
    if not lemma:
        raise HTTPException(status_code=404, detail="Lemma not found")
    return lemma


@router.get("/lemmas", response_model=list[LemmaResponse])
async def search_lemmas(
    word: Optional[str] = Query(None),
    language: str = Query("ru"),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Lemma).where(Lemma.language == language)
    if word:
        query = query.where(Lemma.word.ilike(f"%{word}%"))
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/analyze/{word}", response_model=list[AnalysisResponse])
async def analyze_word(word: str, language: str = Query("ru")):
    """Analyze a word and return its morphological features"""
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
    case: Optional[str] = Query(None),
    number: Optional[str] = Query(None),
):
    """Generate inflected forms from a lemma"""
    engine = MorphologyEngine(language)
    forms = engine.generate(lemma, case=case, number=number)
    return [InflectionResponse(**f) for f in forms]


@router.get("/paradigm/{lemma}", response_model=ParadigmResponse)
async def get_paradigm(lemma: str, language: str = Query("ru"), db: AsyncSession = Depends(get_db)):
    """Get complete paradigm (all forms) for a lemma"""
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
    rule_type: Optional[str] = Query(None),
    pattern_class: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get morphological rules for teaching"""
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

