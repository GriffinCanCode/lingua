"""Curriculum Engine

Smart lesson generation and sentence selection based on:
- User's current mastery levels
- Target patterns for the lesson
- Complexity progression
- Pattern diversity
"""
from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.srs import Sentence, SyntacticPattern, SentencePattern, UserPatternMastery
from models.curriculum import (
    CurriculumSection, CurriculumUnit, CurriculumNode,
    UserNodeProgress, UserUnitProgress,
)


@dataclass(slots=True)
class LessonSentence:
    """Sentence selected for a lesson with metadata."""
    sentence_id: UUID
    text: str
    translation: str | None
    complexity: int
    patterns: list[UUID]
    teaching_value: float  # Higher = better for learning


@dataclass(slots=True)
class Lesson:
    """Generated lesson content."""
    node_id: UUID
    node_title: str
    node_type: str
    target_patterns: list[UUID]
    sentences: list[LessonSentence]
    estimated_duration_min: int
    new_patterns: list[UUID]  # Patterns user hasn't seen
    review_patterns: list[UUID]  # Patterns due for review


@dataclass(slots=True)
class PathProgress:
    """User's overall progress on the learning path."""
    current_section: UUID | None
    current_unit: UUID | None
    current_node: UUID | None
    total_nodes: int
    completed_nodes: int
    crowned_units: int
    streak_days: int
    next_review_count: int
    estimated_daily_time_min: int


class CurriculumEngine:
    """Engine for curriculum management and lesson generation."""

    __slots__ = ("language", "session_length_min", "items_per_minute")

    def __init__(
        self,
        language: str = "ru",
        session_length_min: int = 15,
        items_per_minute: float = 2.0,
    ):
        self.language = language
        self.session_length_min = session_length_min
        self.items_per_minute = items_per_minute

    async def get_learning_path(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> list[dict]:
        """Get the full learning path with user progress."""
        # Get all sections with units and nodes (eager load to avoid lazy loading issues)
        result = await session.execute(
            select(CurriculumSection)
            .options(
                selectinload(CurriculumSection.units).selectinload(CurriculumUnit.nodes)
            )
            .where(
                CurriculumSection.language == self.language,
                CurriculumSection.is_active == True,
            )
            .order_by(CurriculumSection.order_index)
        )
        sections = result.scalars().all()

        # Get user's progress
        progress_result = await session.execute(
            select(UserNodeProgress).where(UserNodeProgress.user_id == user_id)
        )
        node_progress = {p.node_id: p for p in progress_result.scalars().all()}

        unit_progress_result = await session.execute(
            select(UserUnitProgress).where(UserUnitProgress.user_id == user_id)
        )
        unit_progress = {p.unit_id: p for p in unit_progress_result.scalars().all()}

        path = []
        for section in sections:
            section_data = {
                "id": str(section.id),
                "title": section.title,
                "description": section.description,
                "icon": section.icon,
                "color": section.color,
                "units": [],
            }

            for unit in section.units:
                if not unit.is_active:
                    continue

                u_progress = unit_progress.get(unit.id)
                
                # Build nodes first to infer unit status
                nodes_data = []
                completed_count = 0
                has_available = False
                has_in_progress = False
                
                for node in unit.nodes:
                    if not node.is_active:
                        continue
                    n_progress = node_progress.get(node.id)
                    status = n_progress.status if n_progress else "locked"
                    
                    if status == "completed":
                        completed_count += 1
                    elif status == "available":
                        has_available = True
                    elif status == "in_progress":
                        has_in_progress = True
                    
                    nodes_data.append({
                        "id": str(node.id),
                        "title": node.title,
                        "node_type": node.node_type,
                        "status": status,
                        "level": n_progress.level if n_progress else 0,
                        "total_reviews": n_progress.total_reviews if n_progress else 0,
                        "estimated_duration_min": node.estimated_duration_min,
                    })
                
                # Infer unit status from nodes if no explicit progress
                if u_progress:
                    unit_status = u_progress.status
                elif has_in_progress:
                    unit_status = "in_progress"
                elif has_available:
                    unit_status = "available"
                elif completed_count > 0:
                    unit_status = "completed" if completed_count == len(nodes_data) else "in_progress"
                else:
                    unit_status = "locked"
                
                unit_data = {
                    "id": str(unit.id),
                    "title": unit.title,
                    "description": unit.description,
                    "icon": unit.icon,
                    "is_checkpoint": unit.is_checkpoint,
                    "status": unit_status,
                    "is_crowned": u_progress.is_crowned if u_progress else False,
                    "completed_nodes": u_progress.completed_nodes if u_progress else completed_count,
                    "total_nodes": len(nodes_data),
                    "nodes": nodes_data,
                }

                section_data["units"].append(unit_data)

            path.append(section_data)

        return path

    async def get_current_node(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> UUID | None:
        """Get the node the user should work on next."""
        # Find first available or in_progress node
        result = await session.execute(
            select(UserNodeProgress.node_id)
            .where(
                UserNodeProgress.user_id == user_id,
                UserNodeProgress.status.in_(["available", "in_progress"]),
            )
            .order_by(UserNodeProgress.created_at)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row

        # No progress yet - find first node in curriculum
        result = await session.execute(
            select(CurriculumNode.id)
            .join(CurriculumUnit)
            .join(CurriculumSection)
            .where(
                CurriculumSection.language == self.language,
                CurriculumSection.is_active == True,
                CurriculumUnit.is_active == True,
                CurriculumNode.is_active == True,
            )
            .order_by(
                CurriculumSection.order_index,
                CurriculumUnit.order_index,
                CurriculumNode.order_index,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def generate_lesson(
        self,
        session: AsyncSession,
        user_id: UUID,
        node_id: UUID,
        max_sentences: int = 10,
    ) -> Lesson:
        """Generate a lesson for a specific node."""
        # Get node details
        result = await session.execute(
            select(CurriculumNode).where(CurriculumNode.id == node_id)
        )
        node = result.scalar_one()

        # Get user's pattern mastery
        mastery_result = await session.execute(
            select(UserPatternMastery).where(UserPatternMastery.user_id == user_id)
        )
        mastery_map = {m.pattern_id: m for m in mastery_result.scalars().all()}

        # Identify new vs review patterns
        target_patterns = node.target_patterns or []
        new_patterns = [p for p in target_patterns if p not in mastery_map]
        review_patterns = [
            p for p in target_patterns
            if p in mastery_map and mastery_map[p].next_review and mastery_map[p].next_review <= datetime.utcnow()
        ]

        # Get candidate sentences (returns list of (Sentence, patterns) tuples)
        sentences_with_patterns = await self._get_candidate_sentences(
            session, target_patterns, node.complexity_min, node.complexity_max
        )

        # Score and select sentences
        scored_sentences = []
        for sent, patterns in sentences_with_patterns:
            score = self._calculate_teaching_value(patterns, mastery_map, new_patterns, review_patterns)
            scored_sentences.append((score, sent, patterns))

        # Sort by teaching value and diversify
        scored_sentences.sort(key=lambda x: -x[0])
        selected = self._diversify_selection(scored_sentences, max_sentences)

        lesson_sentences = [
            LessonSentence(
                sentence_id=sent.id,
                text=sent.text,
                translation=sent.translation,
                complexity=sent.complexity_score,
                patterns=[sp.pattern_id for sp in patterns],
                teaching_value=score,
            )
            for score, sent, patterns in selected
        ]

        return Lesson(
            node_id=node.id,
            node_title=node.title,
            node_type=node.node_type,
            target_patterns=target_patterns,
            sentences=lesson_sentences,
            estimated_duration_min=node.estimated_duration_min,
            new_patterns=new_patterns,
            review_patterns=review_patterns,
        )

    async def _get_candidate_sentences(
        self,
        session: AsyncSession,
        pattern_ids: list[UUID],
        complexity_min: int,
        complexity_max: int,
        limit: int = 100,
    ) -> list[tuple[Sentence, list[SentencePattern]]]:
        """Get candidate sentences for lesson generation."""
        sentences: list[Sentence] = []
        
        # Try pattern-matched sentences first
        if pattern_ids:
            result = await session.execute(
                select(Sentence)
                .join(SentencePattern)
                .where(
                    SentencePattern.pattern_id.in_(pattern_ids),
                    Sentence.complexity_score >= complexity_min,
                    Sentence.complexity_score <= complexity_max,
                    Sentence.language == self.language,
                )
                .distinct()
                .limit(limit)
            )
            sentences = list(result.scalars().all())

        # Fallback: get any sentences in complexity range if no pattern matches
        if not sentences:
            result = await session.execute(
                select(Sentence)
                .where(
                    Sentence.complexity_score >= complexity_min,
                    Sentence.complexity_score <= complexity_max,
                    Sentence.language == self.language,
                )
                .limit(limit)
            )
            sentences = list(result.scalars().all())

        # Load patterns separately for each sentence (avoid lazy loading)
        sentences_with_patterns: list[tuple[Sentence, list[SentencePattern]]] = []
        for sent in sentences:
            pattern_result = await session.execute(
                select(SentencePattern).where(SentencePattern.sentence_id == sent.id)
            )
            patterns = list(pattern_result.scalars().all())
            sentences_with_patterns.append((sent, patterns))

        return sentences_with_patterns

    def _calculate_teaching_value(
        self,
        patterns: list[SentencePattern],
        mastery_map: dict[UUID, UserPatternMastery],
        new_patterns: list[UUID],
        review_patterns: list[UUID],
    ) -> float:
        """Calculate how valuable a sentence is for teaching."""
        score = 1.0  # Base score
        pattern_ids = [sp.pattern_id for sp in patterns]

        # Bonus for containing new patterns
        new_count = sum(1 for p in pattern_ids if p in new_patterns)
        score += new_count * 3.0

        # Bonus for containing due review patterns
        review_count = sum(1 for p in pattern_ids if p in review_patterns)
        score += review_count * 2.0

        # Bonus for weak patterns (low ease factor)
        for p in pattern_ids:
            if p in mastery_map:
                mastery = mastery_map[p]
                if mastery.ease_factor < 2.0:
                    score += (2.5 - mastery.ease_factor) * 1.5

        # Penalty for too many patterns (cognitive load)
        if len(pattern_ids) > 3:
            score -= (len(pattern_ids) - 3) * 0.5

        # Slight randomization for variety
        import random
        score += random.uniform(0, 0.3)

        return score

    def _diversify_selection(
        self,
        scored_sentences: list[tuple[float, Sentence, list[SentencePattern]]],
        max_count: int,
    ) -> list[tuple[float, Sentence, list[SentencePattern]]]:
        """Select diverse sentences (avoid same patterns/vocabulary)."""
        selected: list[tuple[float, Sentence, list[SentencePattern]]] = []
        seen_patterns: set[UUID] = set()

        for score, sent, patterns in scored_sentences:
            if len(selected) >= max_count:
                break

            sentence_patterns = {sp.pattern_id for sp in patterns}

            # Check for too much overlap
            pattern_overlap = len(sentence_patterns & seen_patterns) / max(len(sentence_patterns), 1)
            if pattern_overlap > 0.8 and len(selected) >= 3:
                continue  # Too similar

            selected.append((score, sent, patterns))
            seen_patterns.update(sentence_patterns)

        return selected

    async def update_node_progress(
        self,
        session: AsyncSession,
        user_id: UUID,
        node_id: UUID,
        correct: int,
        total: int,
    ) -> dict:
        """Update user's progress on a node after completing a lesson."""
        # Get or create progress record
        result = await session.execute(
            select(UserNodeProgress).where(
                UserNodeProgress.user_id == user_id,
                UserNodeProgress.node_id == node_id,
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            progress = UserNodeProgress(
                user_id=user_id,
                node_id=node_id,
                status="in_progress",
                started_at=datetime.utcnow(),
            )
            session.add(progress)

        progress.total_reviews += total
        progress.correct_reviews += correct
        progress.last_practiced_at = datetime.utcnow()

        # Calculate level (0-5 based on accuracy and total reviews)
        if progress.total_reviews >= 5:
            accuracy = progress.correct_reviews / progress.total_reviews
            new_level = min(5, int(accuracy * 5) + (progress.total_reviews // 20))

            if new_level > progress.level:
                progress.level = new_level

            # Check for completion
            if progress.level >= 1 and progress.status != "completed":
                progress.status = "completed"
                progress.completed_at = datetime.utcnow()

                # Unlock next node
                await self._unlock_next_node(session, user_id, node_id)

        await session.flush()

        return {
            "status": progress.status,
            "level": progress.level,
            "total_reviews": progress.total_reviews,
            "accuracy": progress.correct_reviews / max(progress.total_reviews, 1),
        }

    async def _unlock_next_node(
        self,
        session: AsyncSession,
        user_id: UUID,
        completed_node_id: UUID,
    ) -> None:
        """Unlock the next node in the curriculum."""
        # Get the completed node's position
        result = await session.execute(
            select(CurriculumNode).where(CurriculumNode.id == completed_node_id)
        )
        completed_node = result.scalar_one()

        # Find next node in same unit
        result = await session.execute(
            select(CurriculumNode)
            .where(
                CurriculumNode.unit_id == completed_node.unit_id,
                CurriculumNode.order_index > completed_node.order_index,
                CurriculumNode.is_active == True,
            )
            .order_by(CurriculumNode.order_index)
            .limit(1)
        )
        next_node = result.scalar_one_or_none()

        if next_node:
            await self._ensure_node_available(session, user_id, next_node.id)
        else:
            # Unit complete - update unit progress and find next unit
            await self._complete_unit(session, user_id, completed_node.unit_id)

    async def _ensure_node_available(
        self,
        session: AsyncSession,
        user_id: UUID,
        node_id: UUID,
    ) -> None:
        """Ensure a node is marked as available for the user."""
        result = await session.execute(
            select(UserNodeProgress).where(
                UserNodeProgress.user_id == user_id,
                UserNodeProgress.node_id == node_id,
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            progress = UserNodeProgress(
                user_id=user_id,
                node_id=node_id,
                status="available",
            )
            session.add(progress)
        elif progress.status == "locked":
            progress.status = "available"

    async def _complete_unit(
        self,
        session: AsyncSession,
        user_id: UUID,
        unit_id: UUID,
    ) -> None:
        """Mark unit as complete and unlock next unit."""
        # Update unit progress
        result = await session.execute(
            select(UserUnitProgress).where(
                UserUnitProgress.user_id == user_id,
                UserUnitProgress.unit_id == unit_id,
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            progress = UserUnitProgress(
                user_id=user_id,
                unit_id=unit_id,
            )
            session.add(progress)

        progress.status = "completed"
        progress.completed_at = datetime.utcnow()

        # Count completed nodes
        node_result = await session.execute(
            select(func.count(UserNodeProgress.id))
            .join(CurriculumNode)
            .where(
                UserNodeProgress.user_id == user_id,
                CurriculumNode.unit_id == unit_id,
                UserNodeProgress.status == "completed",
            )
        )
        progress.completed_nodes = node_result.scalar() or 0

        # Check for crown (all nodes at level 5)
        crown_result = await session.execute(
            select(func.count(UserNodeProgress.id))
            .join(CurriculumNode)
            .where(
                UserNodeProgress.user_id == user_id,
                CurriculumNode.unit_id == unit_id,
                UserNodeProgress.level >= 5,
            )
        )
        crown_count = crown_result.scalar() or 0

        total_result = await session.execute(
            select(func.count(CurriculumNode.id)).where(
                CurriculumNode.unit_id == unit_id,
                CurriculumNode.is_active == True,
            )
        )
        total_nodes = total_result.scalar() or 0

        if crown_count >= total_nodes and total_nodes > 0:
            progress.is_crowned = True
            progress.crowned_at = datetime.utcnow()

        # Find and unlock next unit
        result = await session.execute(
            select(CurriculumUnit).where(CurriculumUnit.id == unit_id)
        )
        completed_unit = result.scalar_one()

        result = await session.execute(
            select(CurriculumUnit)
            .where(
                CurriculumUnit.section_id == completed_unit.section_id,
                CurriculumUnit.order_index > completed_unit.order_index,
                CurriculumUnit.is_active == True,
            )
            .order_by(CurriculumUnit.order_index)
            .limit(1)
        )
        next_unit = result.scalar_one_or_none()

        if next_unit:
            # Unlock first node of next unit
            result = await session.execute(
                select(CurriculumNode)
                .where(
                    CurriculumNode.unit_id == next_unit.id,
                    CurriculumNode.is_active == True,
                )
                .order_by(CurriculumNode.order_index)
                .limit(1)
            )
            first_node = result.scalar_one_or_none()
            if first_node:
                await self._ensure_node_available(session, user_id, first_node.id)

    async def initialize_user_progress(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> None:
        """Initialize progress for a new user - unlock first node."""
        # Get first node in curriculum
        result = await session.execute(
            select(CurriculumNode.id)
            .join(CurriculumUnit)
            .join(CurriculumSection)
            .where(
                CurriculumSection.language == self.language,
                CurriculumSection.is_active == True,
                CurriculumUnit.is_active == True,
                CurriculumNode.is_active == True,
            )
            .order_by(
                CurriculumSection.order_index,
                CurriculumUnit.order_index,
                CurriculumNode.order_index,
            )
            .limit(1)
        )
        first_node_id = result.scalar_one_or_none()

        if first_node_id:
            await self._ensure_node_available(session, user_id, first_node_id)
            await session.commit()

