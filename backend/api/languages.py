"""Languages API Routes

Provides language configuration and grammar data for frontend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logging import api_logger
from languages import get_module, list_languages

log = api_logger()

router = APIRouter()


# === Response Models ===

class CaseColorResponse(BaseModel):
    bg: str
    text: str
    border: str


class CaseResponse(BaseModel):
    id: str
    label: str
    hint: str
    color: CaseColorResponse


class GenderResponse(BaseModel):
    id: str
    label: str
    short: str


class NumberResponse(BaseModel):
    id: str
    label: str


class GrammarConfigResponse(BaseModel):
    cases: list[CaseResponse]
    genders: list[GenderResponse]
    numbers: list[NumberResponse]
    hasDeclension: bool
    hasConjugation: bool


class LanguageInfoResponse(BaseModel):
    code: str
    name: str
    nativeName: str


# === Endpoints ===

@router.get("/", response_model=list[LanguageInfoResponse])
async def get_available_languages():
    """Get list of available languages."""
    return list_languages()


@router.get("/{lang_code}", response_model=LanguageInfoResponse)
async def get_language_info(lang_code: str):
    """Get language info by code."""
    try:
        module = get_module(lang_code)
        return LanguageInfoResponse(code=module.code, name=module.name, nativeName=module.native_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{lang_code}/grammar", response_model=GrammarConfigResponse)
async def get_grammar_config(lang_code: str):
    """Get grammar configuration (cases, genders, numbers) for frontend."""
    try:
        module = get_module(lang_code)
        config = module.get_grammar_config()
        log.debug("grammar_config_fetched", language=lang_code)
        return config.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{lang_code}/declension-patterns")
async def get_declension_patterns(lang_code: str):
    """Get declension patterns for the language."""
    try:
        module = get_module(lang_code)
        patterns = module.get_declension_patterns()
        return {"patterns": patterns}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
