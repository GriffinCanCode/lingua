"""Ingestion API Routes

Admin endpoints for data ingestion management.
"""
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logging import api_logger
from core.security import get_current_user_id
from core.errors import raise_error, not_found, validation_error
from models.datasource import DataSource, IngestionRecord
from ingest.pipeline import IngestionPipeline

log = api_logger()


router = APIRouter()


# === Request/Response Models ===

class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    language: str
    version: str | None
    url: str | None
    license: str | None
    last_sync: str | None
    is_active: bool
    stats: dict

    class Config:
        from_attributes = True


class IngestionRecordResponse(BaseModel):
    id: UUID
    source_name: str
    language: str
    status: str
    started_at: str | None
    completed_at: str | None
    records_processed: int
    records_created: int
    records_failed: int

    class Config:
        from_attributes = True


class StartIngestionRequest(BaseModel):
    source: str  # universal_dependencies, wiktionary, tatoeba
    file_path: str
    language: str = "ru"
    options: dict = {}


class IngestionStatusResponse(BaseModel):
    record_id: UUID
    status: str
    records_processed: int
    records_created: int
    records_failed: int
    error_count: int


# === Background Task State ===
_active_ingestions: dict[UUID, IngestionRecord] = {}


async def run_ingestion(
    record_id: UUID,
    source: str,
    file_path: str,
    language: str,
    options: dict,
):
    """Background task for running ingestion."""
    pipeline = IngestionPipeline(language=language)

    try:
        if source == "universal_dependencies":
            stats = await pipeline.ingest_ud_corpus(Path(file_path))
        elif source == "wiktionary":
            stats = await pipeline.ingest_wiktionary(Path(file_path))
        elif source == "tatoeba":
            sentences_path = file_path
            links_path = options.get("links_path", "")
            target_lang = options.get("target_lang", "en")
            limit = options.get("limit")
            stats = await pipeline.ingest_tatoeba(
                Path(sentences_path),
                Path(links_path),
                target_lang=target_lang,
                limit=limit,
            )
        else:
            raise ValueError(f"Unknown source: {source}")

        _active_ingestions.pop(record_id, None)

    except Exception as e:
        _active_ingestions.pop(record_id, None)
        raise


# === Endpoints ===

@router.get("/sources", response_model=list[DataSourceResponse])
async def list_data_sources(
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """List all registered data sources."""
    result = await db.execute(
        select(DataSource).where(DataSource.language == language)
    )
    sources = result.scalars().all()

    return [
        DataSourceResponse(
            id=s.id,
            name=s.name,
            language=s.language,
            version=s.version,
            url=s.url,
            license=s.license,
            last_sync=s.last_sync.isoformat() if s.last_sync else None,
            is_active=s.is_active,
            stats=s.stats or {},
        )
        for s in sources
    ]


@router.get("/records", response_model=list[IngestionRecordResponse])
async def list_ingestion_records(
    source_name: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List ingestion records."""
    query = select(IngestionRecord).order_by(IngestionRecord.created_at.desc())

    if source_name:
        query = query.where(IngestionRecord.source_name == source_name)
    if status:
        query = query.where(IngestionRecord.status == status)

    result = await db.execute(query.limit(limit))
    records = result.scalars().all()

    return [
        IngestionRecordResponse(
            id=r.id,
            source_name=r.source_name,
            language=r.language,
            status=r.status,
            started_at=r.started_at.isoformat() if r.started_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            records_processed=r.records_processed,
            records_created=r.records_created,
            records_failed=r.records_failed,
        )
        for r in records
    ]


@router.post("/start", response_model=IngestionStatusResponse)
async def start_ingestion(
    request: StartIngestionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start a new ingestion job."""
    log.info("ingestion_start_requested", source=request.source, file_path=request.file_path)
    
    # Validate source
    valid_sources = {"universal_dependencies", "wiktionary", "tatoeba"}
    if request.source not in valid_sources:
        raise_error(validation_error(
            f"Invalid source. Must be one of: {valid_sources}",
            field="source",
            value=request.source,
            origin="api.ingest",
        ).error)

    # Check file exists
    file_path = Path(request.file_path)
    if not file_path.exists():
        raise_error(not_found("File", str(file_path), origin="api.ingest").error)

    # Create record
    record = IngestionRecord(
        source_name=request.source,
        language=request.language,
        file_path=request.file_path,
        status="pending",
        config=request.options,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Start background task
    background_tasks.add_task(
        run_ingestion,
        record.id,
        request.source,
        request.file_path,
        request.language,
        request.options,
    )

    _active_ingestions[record.id] = record
    log.info("ingestion_job_started", record_id=str(record.id), source=request.source)

    return IngestionStatusResponse(
        record_id=record.id,
        status="pending",
        records_processed=0,
        records_created=0,
        records_failed=0,
        error_count=0,
    )


@router.get("/status/{record_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get status of an ingestion job."""
    result = await db.execute(
        select(IngestionRecord).where(IngestionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise_error(not_found("Ingestion record", record_id, origin="api.ingest").error)

    return IngestionStatusResponse(
        record_id=record.id,
        status=record.status,
        records_processed=record.records_processed,
        records_created=record.records_created,
        records_failed=record.records_failed,
        error_count=len(record.error_log or []),
    )

