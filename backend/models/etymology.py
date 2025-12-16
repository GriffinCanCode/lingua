from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON

from core.database import Base, GUID


class EtymologyNode(Base):
    """Word node in etymology graph"""
    __tablename__ = "etymology_nodes"

    id = Column(GUID, primary_key=True, default=uuid4)
    word = Column(String(255), nullable=False, index=True)
    language = Column(String(50), nullable=False)  # ru, en, la, grc, pie, got, etc.
    language_period = Column(String(100))  # e.g., "Old Church Slavonic", "Proto-Indo-European"
    part_of_speech = Column(String(50))
    meaning = Column(Text)
    pronunciation = Column(String(255))  # IPA or native script
    is_reconstructed = Column(String(1), default="N")  # Y for proto-forms like *gʰerdʰ-
    notes = Column(Text)
    source = Column(String(255))  # Citation/reference
    extra_data = Column(JSON, default=dict)  # Additional properties
    created_at = Column(DateTime, default=datetime.utcnow)


class EtymologyRelation(Base):
    """Relationship between etymology nodes"""
    __tablename__ = "etymology_relations"

    id = Column(GUID, primary_key=True, default=uuid4)
    source_id = Column(GUID, ForeignKey("etymology_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(GUID, ForeignKey("etymology_nodes.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=False)  # cognate, derived_from, borrowed_from, semantic_shift
    confidence = Column(Integer, default=100)  # 0-100 certainty level
    notes = Column(Text)
    source = Column(String(255))  # Citation
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

