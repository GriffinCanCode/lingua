"""Curriculum API Routes

Handles learning path navigation, lesson generation, and progress tracking.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, fetch_one
from core.security import get_current_user_id
from core.errors import raise_result
from models.curriculum import (
    CurriculumSection, CurriculumUnit, CurriculumNode,
    UserNodeProgress, UserUnitProgress,
)
from engines.curriculum import CurriculumEngine


router = APIRouter()


# === Request/Response Models ===

class NodeResponse(BaseModel):
    id: UUID
    title: str
    node_type: str
    status: str
    level: int
    total_reviews: int
    estimated_duration_min: int

    class Config:
        from_attributes = True


class UnitResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    icon: str | None
    is_checkpoint: bool
    status: str
    is_crowned: bool
    completed_nodes: int
    total_nodes: int
    nodes: list[NodeResponse]


class SectionResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    icon: str | None
    color: str | None
    units: list[UnitResponse]


class LessonSentenceResponse(BaseModel):
    sentence_id: UUID
    text: str
    translation: str | None
    complexity: int
    patterns: list[UUID]
    teaching_value: float


class LessonResponse(BaseModel):
    node_id: UUID
    node_title: str
    node_type: str
    target_patterns: list[UUID]
    sentences: list[LessonSentenceResponse]
    estimated_duration_min: int
    new_patterns: list[UUID]
    review_patterns: list[UUID]


class LessonCompleteRequest(BaseModel):
    correct: int
    total: int


class ProgressResponse(BaseModel):
    status: str
    level: int
    total_reviews: int
    accuracy: float


class CurrentNodeResponse(BaseModel):
    node_id: UUID | None
    node_title: str | None
    unit_title: str | None
    section_title: str | None


# === Endpoints ===

@router.get("/path", response_model=list[SectionResponse])
async def get_learning_path(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Get the full learning path with user progress."""
    engine = CurriculumEngine(language=language)
    path = await engine.get_learning_path(db, UUID(user_id))

    # Convert to response models
    return [
        SectionResponse(
            id=UUID(s["id"]),
            title=s["title"],
            description=s.get("description"),
            icon=s.get("icon"),
            color=s.get("color"),
            units=[
                UnitResponse(
                    id=UUID(u["id"]),
                    title=u["title"],
                    description=u.get("description"),
                    icon=u.get("icon"),
                    is_checkpoint=u.get("is_checkpoint", False),
                    status=u.get("status", "locked"),
                    is_crowned=u.get("is_crowned", False),
                    completed_nodes=u.get("completed_nodes", 0),
                    total_nodes=u.get("total_nodes", 0),
                    nodes=[
                        NodeResponse(
                            id=UUID(n["id"]),
                            title=n["title"],
                            node_type=n["node_type"],
                            status=n.get("status", "locked"),
                            level=n.get("level", 0),
                            total_reviews=n.get("total_reviews", 0),
                            estimated_duration_min=n.get("estimated_duration_min", 5),
                        )
                        for n in u.get("nodes", [])
                    ],
                )
                for u in s.get("units", [])
            ],
        )
        for s in path
    ]


@router.get("/current", response_model=CurrentNodeResponse)
async def get_current_node(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Get the current node the user should work on."""
    engine = CurriculumEngine(language=language)
    node_id = await engine.get_current_node(db, UUID(user_id))

    if not node_id:
        return CurrentNodeResponse(
            node_id=None,
            node_title=None,
            unit_title=None,
            section_title=None,
        )

    # Get node details
    result = await db.execute(
        select(CurriculumNode, CurriculumUnit, CurriculumSection)
        .join(CurriculumUnit, CurriculumNode.unit_id == CurriculumUnit.id)
        .join(CurriculumSection, CurriculumUnit.section_id == CurriculumSection.id)
        .where(CurriculumNode.id == node_id)
    )
    row = result.one_or_none()

    if not row:
        return CurrentNodeResponse(
            node_id=node_id,
            node_title=None,
            unit_title=None,
            section_title=None,
        )

    node, unit, section = row
    return CurrentNodeResponse(
        node_id=node.id,
        node_title=node.title,
        unit_title=unit.title,
        section_title=section.title,
    )


@router.get("/nodes/{node_id}/lesson", response_model=LessonResponse)
async def get_lesson(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    max_sentences: int = Query(10, le=20),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a lesson for a specific node."""
    engine = CurriculumEngine(language=language)

    # Verify node exists and is accessible
    result = await db.execute(
        select(UserNodeProgress).where(
            UserNodeProgress.user_id == UUID(user_id),
            UserNodeProgress.node_id == node_id,
        )
    )
    progress = result.scalar_one_or_none()

    # Allow access if no progress (first time) or if available/in_progress
    if progress and progress.status == "locked":
        raise HTTPException(status_code=403, detail="Node is locked")

    lesson = await engine.generate_lesson(db, UUID(user_id), node_id, max_sentences)

    return LessonResponse(
        node_id=lesson.node_id,
        node_title=lesson.node_title,
        node_type=lesson.node_type,
        target_patterns=lesson.target_patterns,
        sentences=[
            LessonSentenceResponse(
                sentence_id=s.sentence_id,
                text=s.text,
                translation=s.translation,
                complexity=s.complexity,
                patterns=s.patterns,
                teaching_value=s.teaching_value,
            )
            for s in lesson.sentences
        ],
        estimated_duration_min=lesson.estimated_duration_min,
        new_patterns=lesson.new_patterns,
        review_patterns=lesson.review_patterns,
    )


@router.post("/nodes/{node_id}/complete", response_model=ProgressResponse)
async def complete_lesson(
    node_id: UUID,
    data: LessonCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Submit lesson completion and update progress."""
    engine = CurriculumEngine(language=language)

    result = await engine.update_node_progress(
        db, UUID(user_id), node_id, data.correct, data.total
    )
    await db.commit()

    return ProgressResponse(**result)


@router.post("/initialize")
async def initialize_progress(
    user_id: str = Depends(get_current_user_id),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Initialize progress for a new user."""
    engine = CurriculumEngine(language=language)
    await engine.initialize_user_progress(db, UUID(user_id))
    return {"status": "initialized"}


@router.get("/sections", response_model=list[SectionResponse])
async def list_sections(
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """List all curriculum sections (admin/preview)."""
    result = await db.execute(
        select(CurriculumSection)
        .where(CurriculumSection.language == language)
        .order_by(CurriculumSection.order_index)
    )
    sections = result.scalars().all()

    response = []
    for section in sections:
        units = []
        for unit in section.units:
            nodes = [
                NodeResponse(
                    id=node.id,
                    title=node.title,
                    node_type=node.node_type,
                    status="preview",
                    level=0,
                    total_reviews=0,
                    estimated_duration_min=node.estimated_duration_min,
                )
                for node in unit.nodes
            ]
            units.append(UnitResponse(
                id=unit.id,
                title=unit.title,
                description=unit.description,
                icon=unit.icon,
                is_checkpoint=unit.is_checkpoint,
                status="preview",
                is_crowned=False,
                completed_nodes=0,
                total_nodes=len(nodes),
                nodes=nodes,
            ))

        response.append(SectionResponse(
            id=section.id,
            title=section.title,
            description=section.description,
            icon=section.icon,
            color=section.color,
            units=units,
        ))

    return response

