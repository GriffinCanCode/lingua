"""Curriculum Models for Lesson-Based Learning Path

Defines the hierarchical structure: Section → Unit → Node
with pattern prerequisites and progression tracking.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Boolean, Index, JSON
from sqlalchemy.orm import relationship

from core.database import Base, GUID


class CurriculumSection(Base):
    """Top-level grouping of curriculum content (e.g., 'Foundations', 'Verbal System')"""
    __tablename__ = "curriculum_sections"
    __table_args__ = (
        Index("ix_curriculum_sections_language_order", "language", "order_index"),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    language = Column(String(10), nullable=False, default="ru")
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False, default=0)
    icon = Column(String(50))  # Icon identifier for UI
    color = Column(String(20))  # Hex color for theming
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    units = relationship("CurriculumUnit", back_populates="section", cascade="all, delete-orphan", order_by="CurriculumUnit.order_index")


class CurriculumUnit(Base):
    """Grouping of related nodes (e.g., 'Genitive Case', 'Present Tense Verbs')"""
    __tablename__ = "curriculum_units"
    __table_args__ = (
        Index("ix_curriculum_units_section_order", "section_id", "order_index"),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    section_id = Column(GUID, ForeignKey("curriculum_sections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False, default=0)
    icon = Column(String(50))
    prerequisite_units = Column(JSON, default=list)  # Unit IDs that must be completed first
    target_patterns = Column(JSON, default=list)  # Pattern IDs covered by this unit
    estimated_duration_min = Column(Integer, default=30)
    is_checkpoint = Column(Boolean, default=False)  # Review unit for entire section
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    section = relationship("CurriculumSection", back_populates="units")
    nodes = relationship("CurriculumNode", back_populates="unit", cascade="all, delete-orphan", order_by="CurriculumNode.order_index")


class CurriculumNode(Base):
    """Individual lesson node within a unit"""
    __tablename__ = "curriculum_nodes"
    __table_args__ = (
        Index("ix_curriculum_nodes_unit_order", "unit_id", "order_index"),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    unit_id = Column(GUID, ForeignKey("curriculum_units.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False, default=0)
    node_type = Column(String(50), nullable=False, default="practice")  # introduction, practice, mixed, checkpoint
    target_patterns = Column(JSON, default=list)  # Specific patterns for this node
    complexity_min = Column(Integer, default=1)
    complexity_max = Column(Integer, default=10)
    min_reviews_to_complete = Column(Integer, default=5)
    sentence_pool_size = Column(Integer, default=0)  # Computed: how many sentences available
    estimated_duration_min = Column(Integer, default=5)
    extra_data = Column(JSON, default=dict)  # Additional config (e.g., exercise types)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unit = relationship("CurriculumUnit", back_populates="nodes")


class UserNodeProgress(Base):
    """Track user progress per curriculum node"""
    __tablename__ = "user_node_progress"
    __table_args__ = (
        Index("ix_user_node_progress_user_node", "user_id", "node_id", unique=True),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    user_id = Column(GUID, nullable=False)
    node_id = Column(GUID, ForeignKey("curriculum_nodes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="locked")  # locked, available, in_progress, completed, needs_practice
    level = Column(Integer, default=0)  # 0-5 mastery level (crowns)
    total_reviews = Column(Integer, default=0)
    correct_reviews = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_practiced_at = Column(DateTime)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserUnitProgress(Base):
    """Track user progress per curriculum unit (aggregated from nodes)"""
    __tablename__ = "user_unit_progress"
    __table_args__ = (
        Index("ix_user_unit_progress_user_unit", "user_id", "unit_id", unique=True),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    user_id = Column(GUID, nullable=False)
    unit_id = Column(GUID, ForeignKey("curriculum_units.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="locked")
    is_crowned = Column(Boolean, default=False)  # All nodes at level 5
    completed_nodes = Column(Integer, default=0)
    total_nodes = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    crowned_at = Column(DateTime)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

