"""Curriculum API Routes

Handles learning path navigation, lesson generation, and progress tracking.
"""
from pathlib import Path
from uuid import UUID
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db, fetch_one
from core.security import get_current_user_id
from core.errors import raise_result
from models.curriculum import (
    CurriculumSection, CurriculumUnit, CurriculumNode,
    UserNodeProgress, UserUnitProgress,
)
from engines.curriculum import CurriculumEngine
from engines.exercises import generate_exercises
from ingest.vocabulary import get_vocabulary_loader

# Path to lesson YAML files
LESSONS_DIR = Path(__file__).parent.parent.parent / "data" / "content" / "lessons"


router = APIRouter()


# === Request/Response Models ===

class NodeResponse(BaseModel):
    id: UUID
    title: str
    level: int
    level_type: str  # intro, easy, medium, hard, review
    status: str
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


class ExerciseResponse(BaseModel):
    id: str
    type: str
    prompt: str
    difficulty: int
    # Dynamic fields based on exercise type
    model_config = {"extra": "allow"}


class LessonExercisesResponse(BaseModel):
    node_id: str
    node_title: str
    level: int
    level_type: str
    exercises: list[dict[str, Any]]
    total_exercises: int
    vocabulary: list[dict[str, Any]]
    content: dict[str, Any] | None = None


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
                            level=n.get("level", 1),
                            level_type=n.get("level_type", "medium"),
                            status=n.get("status", "locked"),
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


def _load_lesson_yaml(lesson_id: str) -> dict[str, Any] | None:
    """Load lesson data from YAML file."""
    # Try different naming patterns
    patterns = [
        f"{lesson_id}.yaml",
        f"unit1_{lesson_id}.yaml",
        lesson_id.replace("-", "_") + ".yaml",
    ]

    for pattern in patterns:
        path = LESSONS_DIR / pattern
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)

    # Search all yaml files for matching lesson
    for yaml_file in LESSONS_DIR.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            if data and data.get("lesson", {}).get("id") == lesson_id:
                return data

    return None


def _find_lesson_by_title(title: str) -> dict[str, Any] | None:
    """Find lesson YAML by title matching."""
    title_lower = title.lower()

    for yaml_file in LESSONS_DIR.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            if not data:
                continue

            # Check lessons list
            lessons = data.get("lessons", [])
            for lesson in lessons:
                if lesson.get("title", "").lower() == title_lower:
                    return {
                        "lesson": lesson,
                        "vocabulary": lesson.get("vocabulary", []),
                        "sentences": lesson.get("sentences", []),
                        "content": lesson.get("content", {}),
                    }

            # Check top-level lesson
            if data.get("lesson", {}).get("title", "").lower() == title_lower:
                return data

    return None


@router.get("/nodes/{node_id}/exercises", response_model=LessonExercisesResponse)
async def get_lesson_exercises(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    num_exercises: int = Query(15, ge=5, le=25),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Generate Duolingo-style exercises for a lesson node. Exercise type distribution is based on the node's level_type."""
    # Get node details
    result = await db.execute(
        select(CurriculumNode).where(CurriculumNode.id == node_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Check access
    progress_result = await db.execute(
        select(UserNodeProgress).where(
            UserNodeProgress.user_id == UUID(user_id),
            UserNodeProgress.node_id == node_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if progress and progress.status == "locked":
        raise HTTPException(status_code=403, detail="Node is locked")

    # Try to load lesson content from YAML first
    lesson_data = _find_lesson_by_title(node.title)
    vocabulary: list[dict] = []
    sentences: list[dict] = []
    review_vocabulary: list[dict] = []
    content: dict | None = None

    if lesson_data:
        vocabulary = lesson_data.get("vocabulary", [])
        sentences = lesson_data.get("sentences", [])
        content = lesson_data.get("content") or lesson_data.get("lesson", {}).get("content")
    else:
        # Fallback: use vocabulary loader with vocab_unit/vocab_lessons from extra_data
        extra = node.extra_data or {}
        vocab_unit = extra.get("vocab_unit")
        vocab_lessons = extra.get("vocab_lessons", [])

        if vocab_unit and vocab_lessons:
            loader = get_vocabulary_loader()

            # Aggregate vocabulary from all referenced lessons
            for vocab_lesson in vocab_lessons:
                lesson_vocab = loader.get_lesson_vocab(vocab_unit, vocab_lesson)
                if lesson_vocab:
                    vocabulary.extend([loader.vocab_to_dict(v) for v in lesson_vocab.primary + lesson_vocab.secondary])
                    review_vocabulary.extend([loader.vocab_to_dict(v) for v in lesson_vocab.review])

                    for v in lesson_vocab.primary:
                        for ex in v.examples:
                            sentences.append({
                                "text": ex.get("ru", ""),
                                "translation": ex.get("en", ""),
                                "complexity": v.difficulty,
                            })

            if vocabulary:
                content = {"introduction": f"Learn {len(vocabulary)} new words!"}

    # Generate exercises based on level type
    exercises = generate_exercises(
        vocabulary=vocabulary,
        sentences=sentences,
        review_vocabulary=review_vocabulary if review_vocabulary else None,
        num_exercises=num_exercises,
        level_type=node.level_type,
    )

    return LessonExercisesResponse(
        node_id=str(node_id),
        node_title=node.title,
        level=node.level,
        level_type=node.level_type,
        exercises=exercises,
        total_exercises=len(exercises),
        vocabulary=vocabulary,
        content=content,
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
        .options(selectinload(CurriculumSection.units).selectinload(CurriculumUnit.nodes))
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

