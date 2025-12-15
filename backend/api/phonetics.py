from typing import Optional
from uuid import UUID
import os

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from engines.phonetics import PhoneticsEngine

router = APIRouter()


class MinimalPair(BaseModel):
    word1: str
    word2: str
    ipa1: str
    ipa2: str
    contrast: str  # e.g., "ы/и", "palatalized/non-palatalized"
    description: str


class PhonemicAnalysis(BaseModel):
    word: str
    ipa: str
    phonemes: list[str]
    syllables: list[str]
    stress_position: Optional[int]


class AcousticFeatures(BaseModel):
    duration_ms: float
    f0_mean: Optional[float]
    f0_range: Optional[tuple[float, float]]
    formants: Optional[dict[str, float]]  # F1, F2, F3


class PronunciationFeedback(BaseModel):
    target_word: str
    target_ipa: str
    user_ipa: str
    accuracy_score: float  # 0-1
    specific_errors: list[dict]
    suggestions: list[str]


@router.get("/minimal-pairs", response_model=list[MinimalPair])
async def get_minimal_pairs(
    contrast: Optional[str] = Query(None, description="Specific contrast to practice, e.g., 'ы/и'"),
    language: str = Query("ru"),
    limit: int = Query(10, le=50),
):
    """Get minimal pairs for phonological training"""
    engine = PhoneticsEngine(language)
    pairs = engine.get_minimal_pairs(contrast=contrast, limit=limit)
    return [MinimalPair(**p) for p in pairs]


@router.get("/analyze/{word}", response_model=PhonemicAnalysis)
async def analyze_phonemes(word: str, language: str = Query("ru")):
    """Get phonemic analysis of a word"""
    engine = PhoneticsEngine(language)
    analysis = engine.analyze_phonemes(word)
    return PhonemicAnalysis(**analysis)


@router.post("/analyze-audio", response_model=AcousticFeatures)
async def analyze_audio(
    audio: UploadFile = File(...),
    language: str = Query("ru"),
):
    """Analyze acoustic features of uploaded audio"""
    if not audio.filename.endswith(('.wav', '.mp3', '.ogg', '.m4a')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    # Save temporarily
    temp_path = f"/tmp/{audio.filename}"
    content = await audio.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        engine = PhoneticsEngine(language)
        features = engine.analyze_audio(temp_path)
        return AcousticFeatures(**features)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/compare-pronunciation", response_model=PronunciationFeedback)
async def compare_pronunciation(
    target_word: str,
    audio: UploadFile = File(...),
    language: str = Query("ru"),
):
    """Compare user pronunciation to target and provide feedback"""
    if not audio.filename.endswith(('.wav', '.mp3', '.ogg', '.m4a')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    temp_path = f"/tmp/{audio.filename}"
    content = await audio.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        engine = PhoneticsEngine(language)
        feedback = engine.compare_pronunciation(target_word, temp_path)
        return PronunciationFeedback(**feedback)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/ipa/{word}")
async def get_ipa(word: str, language: str = Query("ru")):
    """Get IPA transcription for a word"""
    engine = PhoneticsEngine(language)
    return {"word": word, "ipa": engine.get_ipa(word)}


@router.get("/contrasts", response_model=list[dict])
async def get_phonological_contrasts(language: str = Query("ru")):
    """Get list of phonological contrasts for a language that learners need to master"""
    engine = PhoneticsEngine(language)
    return engine.get_contrasts()

