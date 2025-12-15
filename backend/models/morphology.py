from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class Lemma(Base):
    """Base word form (dictionary entry)"""
    __tablename__ = "lemmas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    word = Column(String(255), nullable=False, index=True)
    language = Column(String(10), nullable=False, default="ru")
    part_of_speech = Column(String(50), nullable=False)  # noun, verb, adj, etc.
    gender = Column(String(20))  # masculine, feminine, neuter (for nouns)
    aspect = Column(String(20))  # perfective, imperfective (for verbs)
    declension_class = Column(String(50))  # For pattern matching
    conjugation_class = Column(String(50))  # For pattern matching
    features = Column(JSONB, default=dict)  # Additional morphological features
    definition = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    inflections = relationship("Inflection", back_populates="lemma", cascade="all, delete-orphan")


class MorphologicalRule(Base):
    """Declension/conjugation rules as composable patterns"""
    __tablename__ = "morphological_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    language = Column(String(10), nullable=False, default="ru")
    rule_type = Column(String(50), nullable=False)  # declension, conjugation
    pattern_class = Column(String(50), nullable=False)  # e.g., "1st_declension", "1st_conjugation"
    case = Column(String(20))  # nom, gen, dat, acc, inst, prep (for nouns)
    number = Column(String(10))  # singular, plural
    person = Column(String(10))  # 1st, 2nd, 3rd (for verbs)
    tense = Column(String(20))  # present, past, future (for verbs)
    ending = Column(String(50), nullable=False)  # The actual ending to apply
    stem_modification = Column(String(100))  # How to modify stem before applying ending
    description = Column(Text)  # Human-readable explanation
    examples = Column(JSONB, default=list)  # Example words demonstrating this rule
    created_at = Column(DateTime, default=datetime.utcnow)


class Inflection(Base):
    """Generated/cached inflected forms"""
    __tablename__ = "inflections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lemma_id = Column(UUID(as_uuid=True), ForeignKey("lemmas.id", ondelete="CASCADE"), nullable=False)
    form = Column(String(255), nullable=False, index=True)
    case = Column(String(20))
    number = Column(String(10))
    person = Column(String(10))
    tense = Column(String(20))
    gender = Column(String(20))
    features = Column(JSONB, default=dict)  # Additional features
    
    lemma = relationship("Lemma", back_populates="inflections")

