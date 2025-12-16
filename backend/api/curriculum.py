"""Curriculum API Routes

Handles learning path navigation, lesson generation, and progress tracking.
"""
from pathlib import Path
from uuid import UUID
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db, fetch_one
from core.logging import api_logger
from core.security import get_current_user_id
from core.errors import raise_result, raise_error, not_found, resource_forbidden
from models.curriculum import (
    CurriculumSection, CurriculumUnit, CurriculumNode,
    UserNodeProgress, UserUnitProgress,
)
from engines.curriculum import CurriculumEngine
from engines.exercises import generate_exercises
from engines.templates import TemplateFiller, Template, VocabItem, load_templates
from ingest.vocabulary import get_vocabulary_loader

log = api_logger()


def _load_vocab_for_lesson(lesson_data: dict, unit_id: str, language: str) -> tuple[list[dict], list[dict]]:
    """Load vocabulary based on lesson's vocab_filter."""
    loader = get_vocabulary_loader(language)
    vocab_filter = lesson_data.get("vocab_filter", {})
    
    # Handle both new flat format (primary: [ids]) and old nested format (primary: {ids: [ids]})
    primary_raw = vocab_filter.get("primary", [])
    primary_ids = primary_raw if isinstance(primary_raw, list) else primary_raw.get("ids", [])
    
    unit = loader.load_unit(unit_id)
    if not unit:
        return [], []
    
    vocab_by_id = {v.id: v for v in unit.all_vocab}
    primary = [loader.vocab_to_dict(vocab_by_id[vid]) for vid in primary_ids if vid in vocab_by_id]
    
    # Handle both formats for review: review_from (new) or review.from_lessons (old)
    review: list[dict] = []
    review_lessons = vocab_filter.get("review_from", [])
    if not review_lessons:
        review_raw = vocab_filter.get("review", {})
        review_lessons = review_raw.get("from_lessons", []) if isinstance(review_raw, dict) else []
    
    for lesson_id in review_lessons:
        parts = lesson_id.split("_") if "_" in lesson_id else [lesson_id]
        lesson_key = f"lesson_{parts[0]}_{parts[1]}" if len(parts) > 1 else lesson_id
        lesson_vocab = unit.by_lesson.get(lesson_key)
        if lesson_vocab:
            review.extend([loader.vocab_to_dict(v) for v in lesson_vocab.primary[:3]])
    
    return primary, review


def _generate_sentences_from_templates(lesson_data: dict, vocabulary: list[dict], count: int = 15) -> list[dict]:
    """Generate sentences from templates using vocabulary."""
    templates = load_templates(lesson_data)
    if not templates:
        return []
    
    # Convert vocab dicts to VocabItems
    vocab_items = [
        VocabItem(
            id=v.get("id", v.get("word", "")),
            word=v.get("word", ""),
            translation=v.get("translation", ""),
            pos=v.get("pos", ""),
            gender=v.get("gender"),
            semantic=v.get("semantic", []),
        )
        for v in vocabulary
    ]
    
    filler = TemplateFiller(vocab_items, "ru")
    filled = filler.generate_sentences(templates, count)
    
    # Convert FilledSentences to dict format for exercise generator
    return [
        {
            "text": s.text,
            "translation": s.translation,
            "words": s.words,
            "distractors": s.distractors,
            "complexity": s.complexity,
        }
        for s in filled
    ]

# Base path for content
CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content"


def _parse_modules(raw_modules: list[dict], exercises: list[dict]) -> list["ModuleResponse"]:
    """Parse module definitions and distribute exercises among them."""
    modules = []
    total_exercises = len(exercises)
    exercise_idx = 0
    
    for mod in raw_modules:
        mod_id = mod.get("id", f"mod_{len(modules) + 1}")
        mod_title = mod.get("title", f"Module {len(modules) + 1}")
        mod_type = mod.get("type", "practice")
        
        # Parse teaching content
        teaching = []
        for t in mod.get("teaching", []):
            teaching.append(TeachingContentResponse(
                type=t.get("type", "explanation"),
                title=t.get("title"),
                content=t.get("content"),
                columns=t.get("columns"),
                rows=t.get("rows"),
                word=t.get("word"),
                connections=t.get("connections"),
                insight=t.get("insight"),
                formula=t.get("formula"),
                examples=t.get("examples"),
                rule=t.get("rule"),
                words=t.get("words"),
                points=t.get("points"),
            ))
        
        # Calculate exercise count for this module
        exercise_config = mod.get("exercises", {})
        mod_exercise_count = exercise_config.get("count", 7) if isinstance(exercise_config, dict) else 7
        
        # Distribute remaining exercises proportionally
        remaining_modules = len(raw_modules) - len(modules)
        remaining_exercises = total_exercises - exercise_idx
        actual_count = min(mod_exercise_count, remaining_exercises // max(remaining_modules, 1))
        
        modules.append(ModuleResponse(
            id=mod_id,
            title=mod_title,
            type=mod_type,
            teaching=teaching,
            exercise_count=max(actual_count, 1) if remaining_exercises > 0 else 0,
        ))
        
        exercise_idx += actual_count
    
    return modules


def get_lessons_dirs(language: str) -> list[Path]:
    """Get all lesson directories for a language (one per unit)."""
    lang_dir = CONTENT_DIR / language
    if not lang_dir.exists():
        return []
    return sorted([d / "lessons" for d in lang_dir.iterdir() if d.is_dir() and (d / "lessons").exists()])


router = APIRouter()


# === Request/Response Models ===

class NodeResponse(BaseModel):
    id: UUID
    title: str
    level: int
    level_type: str
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
    model_config = {"extra": "allow"}


class TeachingContentResponse(BaseModel):
    type: str
    title: str | None = None
    content: str | None = None
    columns: list[str] | None = None
    rows: list[list[str]] | None = None
    word: str | None = None
    connections: list[dict[str, str]] | None = None
    insight: str | None = None
    formula: str | None = None
    examples: list[dict[str, str]] | None = None
    rule: str | None = None
    words: list[dict[str, str]] | None = None
    points: list[str] | None = None
    model_config = {"extra": "allow"}


class ModuleResponse(BaseModel):
    id: str
    title: str
    type: str  # intro, learn, pattern, practice, master
    teaching: list[TeachingContentResponse]
    exercise_count: int


class LessonExercisesResponse(BaseModel):
    node_id: str
    node_title: str
    level: int
    level_type: str
    exercises: list[dict[str, Any]]
    total_exercises: int
    vocabulary: list[dict[str, Any]]
    content: dict[str, Any] | None = None
    modules: list[ModuleResponse] | None = None


# === Helper Functions ===

def _load_lesson_yaml(lesson_id: str, language: str = "ru") -> dict[str, Any] | None:
    """Load lesson data from YAML file."""
    for lessons_dir in get_lessons_dirs(language):
        patterns = [f"{lesson_id}.yaml", lesson_id.replace("-", "_") + ".yaml"]
        for pattern in patterns:
            path = lessons_dir / pattern
            if path.exists():
                with open(path) as f:
                    return yaml.safe_load(f)

        for yaml_file in lessons_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                if data and data.get("lesson", {}).get("id") == lesson_id:
                    return data

    return None


def _find_lesson_by_title(title: str, language: str = "ru") -> dict[str, Any] | None:
    """Find lesson YAML by title matching."""
    title_lower = title.lower()

    for lessons_dir in get_lessons_dirs(language):
        for yaml_file in lessons_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                if not data:
                    continue

                # Check lessons list
                for lesson in data.get("lessons", []):
                    if lesson.get("title", "").lower() == title_lower:
                        return {"lesson": lesson, "vocabulary": lesson.get("vocabulary", []), "sentences": lesson.get("sentences", []), "content": lesson.get("content", {})}

                # Check top-level lesson
                if data.get("lesson", {}).get("title", "").lower() == title_lower:
                    return data

    return None


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
        return CurrentNodeResponse(node_id=None, node_title=None, unit_title=None, section_title=None)

    result = await db.execute(
        select(CurriculumNode, CurriculumUnit, CurriculumSection)
        .join(CurriculumUnit, CurriculumNode.unit_id == CurriculumUnit.id)
        .join(CurriculumSection, CurriculumUnit.section_id == CurriculumSection.id)
        .where(CurriculumNode.id == node_id)
    )
    row = result.one_or_none()

    if not row:
        return CurrentNodeResponse(node_id=node_id, node_title=None, unit_title=None, section_title=None)

    node, unit, section = row
    return CurrentNodeResponse(node_id=node.id, node_title=node.title, unit_title=unit.title, section_title=section.title)


@router.get("/nodes/{node_id}/exercises", response_model=LessonExercisesResponse)
async def get_lesson_exercises(
    node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    num_exercises: int = Query(15, ge=5, le=25),
    language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Generate Duolingo-style exercises for a lesson node."""
    log.debug("get_lesson_exercises", node_id=str(node_id), user_id=user_id, num_exercises=num_exercises, language=language)

    result = await db.execute(
        select(CurriculumNode, CurriculumUnit)
        .join(CurriculumUnit, CurriculumNode.unit_id == CurriculumUnit.id)
        .where(CurriculumNode.id == node_id)
    )
    row = result.one_or_none()
    if not row:
        raise_error(not_found("Node", node_id, origin="api.curriculum").error)
    
    node, unit = row

    progress_result = await db.execute(
        select(UserNodeProgress).where(UserNodeProgress.user_id == UUID(user_id), UserNodeProgress.node_id == node_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress and progress.status == "locked":
        raise_error(resource_forbidden(f"Node {node_id}", user_id, origin="api.curriculum").error)

    # Load lesson content with language awareness
    lesson_data = _find_lesson_by_title(node.title, language)
    vocabulary: list[dict] = []
    sentences: list[dict] = []
    review_vocabulary: list[dict] = []
    content: dict | None = None

    if lesson_data:
        vocabulary = lesson_data.get("vocabulary", [])
        sentences = lesson_data.get("sentences", [])
        content = lesson_data.get("content") or lesson_data.get("lesson", {}).get("content")

        # Handle dynamic content generation
        if not vocabulary and "vocab_filter" in lesson_data:
            vocab_unit_id = unit.extra_data.get("original_id", "unit1") if unit.extra_data else "unit1"
            primary, review = _load_vocab_for_lesson(lesson_data, vocab_unit_id, language)
            vocabulary = primary
            review_vocabulary = review
        
        if not sentences and "templates" in lesson_data and vocabulary:
            sentences = _generate_sentences_from_templates(lesson_data, vocabulary, num_exercises)
    else:
        extra = node.extra_data or {}
        vocab_unit = extra.get("vocab_unit")
        vocab_lessons = extra.get("vocab_lessons", [])

        if vocab_unit and vocab_lessons:
            loader = get_vocabulary_loader()

            for vocab_lesson in vocab_lessons:
                lesson_vocab = loader.get_lesson_vocab(vocab_unit, vocab_lesson)
                if lesson_vocab:
                    vocabulary.extend([loader.vocab_to_dict(v) for v in lesson_vocab.primary + lesson_vocab.secondary])
                    review_vocabulary.extend([loader.vocab_to_dict(v) for v in lesson_vocab.review])

                    for v in lesson_vocab.primary:
                        for ex in v.examples:
                            sentences.append({"text": ex.get("ru", ""), "translation": ex.get("en", ""), "complexity": v.difficulty})

            if vocabulary:
                content = {"introduction": f"Learn {len(vocabulary)} new words!"}

    # Extract dialogues from lesson data for dialogue exercises
    dialogues = lesson_data.get("dialogues", []) if lesson_data else []

    exercises = generate_exercises(
        vocabulary=vocabulary,
        sentences=sentences,
        review_vocabulary=review_vocabulary if review_vocabulary else None,
        num_exercises=num_exercises,
        level_type=node.level_type,
        language=language,
        dialogues=dialogues,
    )

    # Parse modules from lesson data if available
    modules = None
    if lesson_data:
        raw_modules = lesson_data.get("modules", [])
        if raw_modules:
            modules = _parse_modules(raw_modules, exercises)
    
    # Include modules in content for frontend compatibility
    if modules and content:
        content["modules"] = [m.model_dump() for m in modules]
    elif modules:
        content = {"modules": [m.model_dump() for m in modules]}

    log.info("exercises_generated", node_id=str(node_id), exercise_count=len(exercises), module_count=len(modules) if modules else 0, language=language)
    return LessonExercisesResponse(
        node_id=str(node_id),
        node_title=node.title,
        level=node.level,
        level_type=node.level_type,
        exercises=exercises,
        total_exercises=len(exercises),
        vocabulary=vocabulary,
        content=content,
        modules=modules,
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
    result = await engine.update_node_progress(db, UUID(user_id), node_id, data.correct, data.total)
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
                    level_type=node.level_type,
                    status="preview",
                    level=node.level,
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
