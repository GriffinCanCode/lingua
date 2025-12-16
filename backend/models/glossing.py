from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from core.database import Base, GUID


class GlossedText(Base):
    """Text with interlinear glossing annotations"""
    __tablename__ = "glossed_texts"

    id = Column(GUID, primary_key=True, default=uuid4)
    title = Column(String(255))
    original_text = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default="ru")
    translation = Column(Text)
    source = Column(String(255))
    difficulty = Column(Integer, default=1)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    morphemes = relationship("Morpheme", back_populates="text", cascade="all, delete-orphan")


class Morpheme(Base):
    """Individual morpheme with Leipzig glossing"""
    __tablename__ = "morphemes"

    id = Column(GUID, primary_key=True, default=uuid4)
    text_id = Column(GUID, ForeignKey("glossed_texts.id", ondelete="CASCADE"), nullable=False)
    word_index = Column(Integer, nullable=False)  # Position in sentence
    morpheme_index = Column(Integer, nullable=False)  # Position within word
    surface_form = Column(String(255), nullable=False)  # The actual morpheme
    gloss = Column(String(255), nullable=False)  # Leipzig gloss (e.g., "1SG", "ACC", "PRS")
    morpheme_type = Column(String(50))  # root, prefix, suffix, infix, etc.
    lemma = Column(String(255))  # Base form if applicable
    features = Column(JSON, default=dict)  # Additional morphological features
    
    text = relationship("GlossedText", back_populates="morphemes")

