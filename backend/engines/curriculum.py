"""Curriculum Engine

Handles learning path navigation and progress tracking for Duolingo-style curriculum.
"""
from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.curriculum import (
    CurriculumSection, CurriculumUnit, CurriculumNode,
    UserNodeProgress, UserUnitProgress,
)


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
                        "level": node.level,
                        "level_type": node.level_type,
                        "status": status,
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

