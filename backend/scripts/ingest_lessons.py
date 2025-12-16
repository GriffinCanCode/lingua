#!/usr/bin/env python3
"""Ingest lesson content from YAML files into the database.

Reads YAML files from data/content/lessons/ and populates:
- CurriculumSection
- CurriculumUnit
- CurriculumNode
- Sentences (and links them to nodes via extra_data)

Run with: python3 -m scripts.ingest_lessons
"""
import asyncio
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session, engine, Base
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode
from models.srs import Sentence, SyntacticPattern

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content" / "lessons"

async def get_or_create_section(session: AsyncSession, data: Dict[str, Any]) -> CurriculumSection:
    """Get or create a curriculum section."""
    stmt = select(CurriculumSection).where(
        CurriculumSection.title == data["title"],
        CurriculumSection.language == "ru" # Assuming Russian for now
    )
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        section = CurriculumSection(
            title=data["title"],
            description=data.get("description"),
            order_index=data.get("order", 0),
            language="ru"
        )
        session.add(section)
        await session.flush()
        logger.info(f"Created Section: {section.title}")
    else:
        # Update fields
        section.description = data.get("description", section.description)
        section.order_index = data.get("order", section.order_index)
        logger.info(f"Updated Section: {section.title}")
    
    return section

async def get_or_create_unit(session: AsyncSession, section: CurriculumSection, data: Dict[str, Any]) -> CurriculumUnit:
    """Get or create a curriculum unit."""
    stmt = select(CurriculumUnit).where(
        CurriculumUnit.section_id == section.id,
        CurriculumUnit.title == data["title"]
    )
    result = await session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        unit = CurriculumUnit(
            section_id=section.id,
            title=data["title"],
            description=data.get("description"),
            order_index=data.get("order", 0),
            prerequisite_units=[], # TODO: Handle prerequisites by ID lookup
            target_patterns=[] # TODO: Aggregate from lessons
        )
        session.add(unit)
        await session.flush()
        logger.info(f"Created Unit: {unit.title}")
    else:
        unit.description = data.get("description", unit.description)
        unit.order_index = data.get("order", unit.order_index)
        logger.info(f"Updated Unit: {unit.title}")

    return unit

async def get_or_create_pattern(session: AsyncSession, pattern_id: str) -> UUID:
    """Get pattern ID by name (creating a placeholder if missing is risky, better to warn)."""
    # For now, we assume patterns exist or we just log a warning.
    # In a real scenario, we might want to create them or fail.
    stmt = select(SyntacticPattern).where(SyntacticPattern.pattern_type == pattern_id)
    result = await session.execute(stmt)
    pattern = result.scalar_one_or_none()
    
    if pattern:
        return pattern.id
    else:
        logger.warning(f"Pattern not found: {pattern_id}")
        return None

async def ingest_lesson(session: AsyncSession, unit: CurriculumUnit, data: Dict[str, Any]):
    """Ingest a single lesson (node)."""
    stmt = select(CurriculumNode).where(
        CurriculumNode.unit_id == unit.id,
        CurriculumNode.title == data["title"]
    )
    result = await session.execute(stmt)
    node = result.scalar_one_or_none()

    # Process patterns
    pattern_ids = []
    if "patterns" in data:
        for p_name in data["patterns"]:
            p_id = await get_or_create_pattern(session, p_name)
            if p_id:
                pattern_ids.append(p_id)

    # Process Sentences
    featured_sentence_ids = []
    if "sentences" in data:
        for s_data in data["sentences"]:
            # Check if sentence exists by text
            stmt = select(Sentence).where(Sentence.text == s_data["text"])
            result = await session.execute(stmt)
            sentence = result.scalars().first()
            
            if not sentence:
                sentence = Sentence(
                    text=s_data["text"],
                    translation=s_data.get("translation"),
                    complexity_score=s_data.get("complexity", 1),
                    language="ru",
                    extra_data={"audio": s_data.get("audio")}
                )
                session.add(sentence)
                await session.flush()
                logger.info(f"Created Sentence: {sentence.text[:20]}...")
            
            featured_sentence_ids.append(str(sentence.id))

    # Process Vocabulary (store in extra_data for now)
    vocabulary = data.get("vocabulary", [])

    extra_data = {
        "featured_sentences": featured_sentence_ids,
        "vocabulary": vocabulary,
        "content": data.get("content", {})
    }

    if not node:
        node = CurriculumNode(
            unit_id=unit.id,
            title=data["title"],
            description=data.get("description"),
            order_index=data.get("order", 0),
            node_type=data.get("type", "practice"),
            target_patterns=pattern_ids,
            extra_data=extra_data,
            estimated_duration_min=5 # Default
        )
        session.add(node)
        logger.info(f"Created Lesson: {node.title}")
    else:
        node.description = data.get("description", node.description)
        node.order_index = data.get("order", node.order_index)
        node.extra_data = extra_data
        node.target_patterns = pattern_ids
        logger.info(f"Updated Lesson: {node.title}")

async def process_file(session: AsyncSession, file_path: Path):
    """Process a single YAML file."""
    logger.info(f"Processing {file_path.name}...")
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    if not data:
        return

    # 1. Section
    section = await get_or_create_section(session, data["section"])

    # 2. Unit
    unit = await get_or_create_unit(session, section, data["unit"])

    # 3. Lessons
    for lesson_data in data.get("lessons", []):
        await ingest_lesson(session, unit, lesson_data)

async def main():
    """Main entry point."""
    if not CONTENT_DIR.exists():
        logger.error(f"Content directory not found: {CONTENT_DIR}")
        return

    async with get_db_session() as session:
        files = sorted(CONTENT_DIR.glob("*.yaml"))
        for file_path in files:
            await process_file(session, file_path)
        
        await session.commit()
        logger.info("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
