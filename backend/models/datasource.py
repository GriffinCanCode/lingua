"""Data Source Models for Tracking Ingestion

Tracks external data sources (UD, Wiktionary, Tatoeba) and
individual records for deduplication and updates.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base


class DataSource(Base):
    """External data source registry"""
    __tablename__ = "data_sources"
    __table_args__ = (
        Index("ix_data_sources_name_lang", "name", "language"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)  # universal_dependencies, wiktionary, tatoeba, openrussian
    language = Column(String(10), nullable=False, default="ru")
    version = Column(String(50))  # e.g., "2.14" for UD, date for wiktionary dump
    url = Column(String(500))  # Source URL
    license = Column(String(100))  # e.g., "CC-BY-SA-4.0"
    description = Column(Text)
    last_sync = Column(DateTime)
    next_sync = Column(DateTime)
    sync_frequency_days = Column(Integer, default=90)
    is_active = Column(Boolean, default=True)
    config = Column(JSONB, default=dict)  # Source-specific configuration
    stats = Column(JSONB, default=dict)  # Import statistics
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IngestionRecord(Base):
    """Track individual ingestion runs for audit and rollback"""
    __tablename__ = "ingestion_records"
    __table_args__ = (
        Index("ix_ingestion_records_source_status", "source_name", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_name = Column(String(100), nullable=False)
    language = Column(String(10), nullable=False, default="ru")
    file_path = Column(String(500))  # Original file processed
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_log = Column(JSONB, default=list)  # List of error messages
    config = Column(JSONB, default=dict)  # Run configuration
    stats = Column(JSONB, default=dict)  # Additional statistics
    created_at = Column(DateTime, default=datetime.utcnow)


class ExternalIdMapping(Base):
    """Map external IDs to internal UUIDs for deduplication"""
    __tablename__ = "external_id_mappings"
    __table_args__ = (
        Index("ix_external_id_unique", "source_name", "external_id", "entity_type", unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_name = Column(String(100), nullable=False)
    external_id = Column(String(255), nullable=False)  # ID in external system
    entity_type = Column(String(50), nullable=False)  # sentence, lemma, pattern, etc.
    internal_id = Column(UUID(as_uuid=True), nullable=False)  # Our UUID
    version = Column(String(50))  # Version when imported
    checksum = Column(String(64))  # For detecting changes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

