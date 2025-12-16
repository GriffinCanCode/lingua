from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship

from core.database import Base, GUID


class Sentence(Base):
    """Curated sentences with syntactic annotations"""
    __tablename__ = "sentences"

    id = Column(GUID, primary_key=True, default=uuid4)
    text = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default="ru")
    translation = Column(Text)
    complexity_score = Column(Integer, default=1)  # 1-10 difficulty
    audio_path = Column(String(500))  # Path to audio file
    source = Column(String(255))  # Where the sentence came from
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    patterns = relationship("SentencePattern", back_populates="sentence", cascade="all, delete-orphan")


class SyntacticPattern(Base):
    """Grammatical patterns to track"""
    __tablename__ = "syntactic_patterns"

    id = Column(GUID, primary_key=True, default=uuid4)
    pattern_type = Column(String(100), nullable=False)  # e.g., "genitive_plural_after_preposition"
    language = Column(String(10), nullable=False, default="ru")
    features = Column(JSON, nullable=False)  # UD features: case, number, tense, etc.
    description = Column(Text)
    difficulty = Column(Integer, default=1)  # Base difficulty 1-10
    examples = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    sentence_patterns = relationship("SentencePattern", back_populates="pattern", cascade="all, delete-orphan")


class SentencePattern(Base):
    """Junction table linking sentences to patterns"""
    __tablename__ = "sentence_patterns"

    id = Column(GUID, primary_key=True, default=uuid4)
    sentence_id = Column(GUID, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False)
    pattern_id = Column(GUID, ForeignKey("syntactic_patterns.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50))  # How this pattern appears in the sentence
    position = Column(Integer)  # Word position in sentence
    
    sentence = relationship("Sentence", back_populates="patterns")
    pattern = relationship("SyntacticPattern", back_populates="sentence_patterns")


class UserPatternMastery(Base):
    """Track user mastery per grammatical pattern (SRS data)"""
    __tablename__ = "user_pattern_mastery"

    id = Column(GUID, primary_key=True, default=uuid4)
    user_id = Column(GUID, nullable=False)
    pattern_id = Column(GUID, ForeignKey("syntactic_patterns.id", ondelete="CASCADE"), nullable=False)
    ease_factor = Column(Float, default=2.5)  # SM-2 ease factor
    interval = Column(Integer, default=1)  # Days until next review
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime)
    last_review = Column(DateTime)
    total_reviews = Column(Integer, default=0)
    correct_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

