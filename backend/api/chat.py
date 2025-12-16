"""Chat API for AI-powered conversation practice."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engines.chat import get_chat_engine, ChatSession, ChatMessage as EngineChatMessage

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store (use Redis/DB in production)
_sessions: dict[str, ChatSession] = {}


class StartSessionRequest(BaseModel):
    mode: Literal['guided', 'freeform'] = 'guided'
    lesson_context: str | None = None
    vocabulary: list[str] | None = None


class StartSessionResponse(BaseModel):
    session_id: str
    mode: str
    greeting: str


class SendMessageRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    corrections: list[dict] | None = None
    translation: str | None = None


class CorrectionsRequest(BaseModel):
    sentence: str


class CorrectionsResponse(BaseModel):
    corrections: list[dict]
    is_correct: bool


class TranslateRequest(BaseModel):
    text: str
    to_lang: Literal['ru', 'en'] = 'en'


class TranslateResponse(BaseModel):
    translation: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    mode: str
    messages: list[ChatMessageResponse]


@router.post("/start", response_model=StartSessionResponse)
async def start_chat(request: StartSessionRequest):
    """Initialize a new chat session."""
    engine = get_chat_engine()
    session = await engine.start_session(
        mode=request.mode,
        lesson_context=request.lesson_context,
        vocabulary=request.vocabulary,
    )
    
    # Store session
    _sessions[session.id] = session
    
    # Generate initial greeting
    greeting_msg = await engine.send_message(session, "Привет!")
    
    return StartSessionResponse(
        session_id=session.id,
        mode=session.mode,
        greeting=greeting_msg.content,
    )


@router.post("/{session_id}/message", response_model=ChatMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """Send a message in an existing chat session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    engine = get_chat_engine()
    response = await engine.send_message(session, request.message)
    
    return ChatMessageResponse(
        id=response.id,
        role=response.role,
        content=response.content,
        corrections=response.corrections,
        translation=response.translation,
    )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_history(session_id: str):
    """Get conversation history for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Filter out system messages
    messages = [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            corrections=m.corrections,
            translation=m.translation,
        )
        for m in session.messages
        if m.role != 'system'
    ]
    
    return ChatHistoryResponse(
        session_id=session.id,
        mode=session.mode,
        messages=messages,
    )


@router.post("/feedback", response_model=CorrectionsResponse)
async def get_feedback(request: CorrectionsRequest):
    """Get grammar corrections for a Russian sentence."""
    engine = get_chat_engine()
    result = await engine.get_corrections(request.sentence)
    
    return CorrectionsResponse(
        corrections=result.get('corrections', []),
        is_correct=result.get('is_correct', True),
    )


@router.post("/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """Translate text between Russian and English."""
    engine = get_chat_engine()
    translation = await engine.translate(request.text, request.to_lang)
    
    return TranslateResponse(translation=translation)


@router.delete("/{session_id}")
async def end_session(session_id: str):
    """End a chat session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "ended"}
    raise HTTPException(status_code=404, detail="Session not found")
