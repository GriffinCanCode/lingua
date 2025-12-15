from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base


class ProductionPrompt(Base):
    """Prompts for production exercises"""
    __tablename__ = "production_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    prompt_type = Column(String(50), nullable=False)  # translation, fill_blank, free_production
    language = Column(String(10), nullable=False, default="ru")
    prompt_text = Column(Text, nullable=False)  # The prompt shown to user
    expected_patterns = Column(JSONB, default=list)  # Pattern IDs to practice
    target_structures = Column(JSONB, default=list)  # Expected grammatical structures
    acceptable_answers = Column(JSONB, default=list)  # Valid responses
    hints = Column(JSONB, default=list)  # Progressive hints
    difficulty = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductionAttempt(Base):
    """User attempts at production exercises"""
    __tablename__ = "production_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("production_prompts.id", ondelete="CASCADE"), nullable=False)
    user_response = Column(Text, nullable=False)
    is_correct = Column(String(1), default="N")  # Y/N/P (partial)
    score = Column(Float, default=0.0)  # 0-1 score
    time_taken_seconds = Column(Integer)
    audio_path = Column(String(500))  # Path to voice recording if applicable
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductionFeedback(Base):
    """Detailed feedback on production attempts"""
    __tablename__ = "production_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("production_attempts.id", ondelete="CASCADE"), nullable=False)
    error_type = Column(String(50))  # morphological, syntactic, semantic, phonetic
    error_description = Column(Text)
    correction = Column(Text)
    explanation = Column(Text)
    related_pattern_id = Column(UUID(as_uuid=True), ForeignKey("syntactic_patterns.id", ondelete="SET NULL"))
    severity = Column(Integer, default=1)  # 1-5 severity
    created_at = Column(DateTime, default=datetime.utcnow)

