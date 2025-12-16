"""Chat Engine for AI-powered conversation practice.

Provides guided and freeform Russian conversation with an AI tutor,
including grammar correction and vocabulary-aware responses.
"""
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from openai import AsyncOpenAI

from core.config import settings
from core.logging import engine_logger

log = engine_logger()

ChatMode = Literal['guided', 'freeform']
MessageRole = Literal['user', 'assistant', 'system']


@dataclass(slots=True)
class ChatMessage:
    """Single message in conversation."""
    id: str
    role: MessageRole
    content: str
    corrections: list[dict] | None = None
    translation: str | None = None


@dataclass(slots=True)
class ChatSession:
    """Chat session state."""
    id: str
    mode: ChatMode
    lesson_context: str | None = None
    vocabulary: list[str] = field(default_factory=list)
    messages: list[ChatMessage] = field(default_factory=list)


SYSTEM_PROMPTS = {
    'guided': """You are a friendly Russian language tutor named Маша. You're having a conversation practice session with a student.

Rules:
- Speak primarily in Russian, using simple vocabulary appropriate for beginners
- Keep responses short (1-2 sentences max)
- If the student makes grammar mistakes, gently note them but keep the conversation flowing
- Use the vocabulary words provided when possible: {vocabulary}
- Topic context: {context}
- Occasionally ask simple questions to keep the student engaged
- If the student writes in English, respond in Russian but acknowledge their message

Response format: Just respond naturally in Russian. Do not include translations unless asked.""",

    'freeform': """You are a friendly Russian language tutor named Маша. You're having a free-form conversation practice.

Rules:
- Speak in Russian, adjusting complexity to match the student's level
- Keep responses conversational (2-3 sentences max)
- If the student makes grammar mistakes, you can briefly mention them
- Be encouraging and supportive
- Feel free to discuss any topic the student brings up
- If the student writes in English, respond in Russian but acknowledge their message

Response format: Just respond naturally in Russian.""",
}

CORRECTION_PROMPT = """Analyze this Russian sentence for grammar and spelling errors. Be concise.

Sentence: "{sentence}"

Provide corrections in this JSON format:
{{"corrections": [{{"original": "word", "corrected": "word", "explanation": "brief reason"}}], "is_correct": true/false}}

If no errors, return: {{"corrections": [], "is_correct": true}}"""


class ChatEngine:
    """Handles AI-powered Russian conversation practice."""

    __slots__ = ('_client', '_model', '_max_tokens')

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self._model = settings.OPENAI_MODEL
        self._max_tokens = settings.CHAT_MAX_TOKENS
        log.debug("chat_engine_initialized", model=self._model, has_key=bool(settings.OPENAI_API_KEY))

    async def start_session(
        self,
        mode: ChatMode = 'guided',
        lesson_context: str | None = None,
        vocabulary: list[str] | None = None,
    ) -> ChatSession:
        """Initialize a new chat session."""
        session = ChatSession(
            id=str(uuid4()),
            mode=mode,
            lesson_context=lesson_context,
            vocabulary=vocabulary or [],
        )
        
        # Add system message
        system_prompt = SYSTEM_PROMPTS[mode].format(
            vocabulary=', '.join(vocabulary or []),
            context=lesson_context or 'General conversation',
        )
        session.messages.append(ChatMessage(id=str(uuid4()), role='system', content=system_prompt))
        
        log.info("chat_session_started", session_id=session.id, mode=mode)
        return session

    async def send_message(self, session: ChatSession, user_message: str) -> ChatMessage:
        """Send user message and get AI response."""
        if not self._client:
            return self._fallback_response(user_message)

        # Add user message to history
        user_msg = ChatMessage(id=str(uuid4()), role='user', content=user_message)
        session.messages.append(user_msg)

        # Build messages for API
        api_messages = [{'role': m.role, 'content': m.content} for m in session.messages]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=api_messages,
                max_tokens=self._max_tokens,
                temperature=0.7,
            )
            
            ai_content = response.choices[0].message.content or "..."
            ai_msg = ChatMessage(id=str(uuid4()), role='assistant', content=ai_content)
            session.messages.append(ai_msg)
            
            log.debug("chat_response_generated", session_id=session.id, tokens=response.usage.total_tokens if response.usage else 0)
            return ai_msg

        except Exception as e:
            log.error("chat_api_error", error=str(e))
            return self._fallback_response(user_message)

    async def get_corrections(self, sentence: str) -> dict:
        """Get grammar corrections for a Russian sentence."""
        if not self._client:
            return {'corrections': [], 'is_correct': True}

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'user', 'content': CORRECTION_PROMPT.format(sentence=sentence)}],
                max_tokens=200,
                temperature=0,
            )
            
            content = response.choices[0].message.content or '{}'
            # Parse JSON response
            import json
            try:
                return json.loads(content.strip('`').replace('json\n', ''))
            except json.JSONDecodeError:
                return {'corrections': [], 'is_correct': True, 'raw': content}

        except Exception as e:
            log.error("correction_api_error", error=str(e))
            return {'corrections': [], 'is_correct': True, 'error': str(e)}

    async def translate(self, text: str, to_lang: Literal['ru', 'en'] = 'en') -> str:
        """Translate text between Russian and English."""
        if not self._client:
            return text

        direction = "Russian to English" if to_lang == 'en' else "English to Russian"
        prompt = f"Translate this from {direction}. Only return the translation, nothing else.\n\n{text}"

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=200,
                temperature=0,
            )
            return response.choices[0].message.content or text

        except Exception as e:
            log.error("translation_error", error=str(e))
            return text

    def _fallback_response(self, user_message: str) -> ChatMessage:
        """Return a fallback response when API is unavailable."""
        responses = [
            "Привет! Как дела? (API key not configured)",
            "Интересно! (API key not configured)",
            "Хорошо! (API key not configured)",
        ]
        import random
        return ChatMessage(
            id=str(uuid4()),
            role='assistant',
            content=random.choice(responses),
        )


# Singleton instance
_engine: ChatEngine | None = None


def get_chat_engine() -> ChatEngine:
    """Get or create the chat engine singleton."""
    global _engine
    if _engine is None:
        _engine = ChatEngine()
    return _engine
