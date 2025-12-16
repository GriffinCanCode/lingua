from pathlib import Path
import logging
import argparse
import yaml
import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session, engine, Base
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode
from models.srs import Sentence, SyntacticPattern

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content"


def get_lessons_dirs(language: str) -> list[Path]:
    """Get all lesson directories for a language (one per unit)."""
    lang_dir = CONTENT_DIR / language
    if not lang_dir.exists():
        return []
    return sorted([d / "lessons" for d in lang_dir.iterdir() if d.is_dir() and (d / "lessons").exists()])


async def get_or_create_section(session: AsyncSession, data: dict, language: str) -> CurriculumSection:
    """Get or create a curriculum section."""
    stmt = select(CurriculumSection).where(CurriculumSection.title == data["title"], CurriculumSection.language == language)
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        section = CurriculumSection(title=data["title"], description=data.get("description"), order_index=data.get("order", 0), language=language)
        session.add(section)
        await session.flush()
        logger.info(f"Created Section: {section.title}")
    else:
        section.description = data.get("description", section.description)
        section.order_index = data.get("order", section.order_index)
        logger.info(f"Updated Section: {section.title}")

    return section


async def get_or_create_unit(session: AsyncSession, section: CurriculumSection, data: dict) -> CurriculumUnit:
    """Get or create a curriculum unit."""
    stmt = select(CurriculumUnit).where(CurriculumUnit.section_id == section.id, CurriculumUnit.title == data["title"])
    result = await session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        unit = CurriculumUnit(
            section_id=section.id,
            title=data["title"],
            description=data.get("description"),
            order_index=data.get("order", 0),
            prerequisite_units=[],
            target_patterns=[],
        )
        session.add(unit)
        await session.flush()
        logger.info(f"Created Unit: {unit.title}")
    else:
        unit.description = data.get("description", unit.description)
        unit.order_index = data.get("order", unit.order_index)
        logger.info(f"Updated Unit: {unit.title}")

    return unit


async def get_or_create_pattern(session: AsyncSession, pattern_id: str) -> UUID | None:
    """Get pattern ID by name."""
    stmt = select(SyntacticPattern).where(SyntacticPattern.pattern_type == pattern_id)
    result = await session.execute(stmt)
    pattern = result.scalar_one_or_none()

    if pattern:
        return pattern.id
    logger.warning(f"Pattern not found: {pattern_id}")
    return None


async def ingest_lesson(session: AsyncSession, unit: CurriculumUnit, data: dict, language: str):
    """Ingest a single lesson (node)."""
    stmt = select(CurriculumNode).where(CurriculumNode.unit_id == unit.id, CurriculumNode.title == data["title"])
    result = await session.execute(stmt)
    node = result.scalar_one_or_none()

    pattern_ids = []
    if "patterns" in data:
        for p_name in data["patterns"]:
            p_id = await get_or_create_pattern(session, p_name)
            if p_id:
                pattern_ids.append(p_id)

    featured_sentence_ids = []
    if "sentences" in data:
        for s_data in data["sentences"]:
            stmt = select(Sentence).where(Sentence.text == s_data["text"])
            result = await session.execute(stmt)
            sentence = result.scalars().first()

            if not sentence:
                sentence = Sentence(
                    text=s_data["text"],
                    translation=s_data.get("translation"),
                    complexity_score=s_data.get("complexity", 1),
                    language=language,
                    extra_data={"audio": s_data.get("audio")},
                )
                session.add(sentence)
                await session.flush()
                logger.info(f"Created Sentence: {sentence.text[:20]}...")

            featured_sentence_ids.append(str(sentence.id))

    vocabulary = data.get("vocabulary", [])
    extra_data = {"featured_sentences": featured_sentence_ids, "vocabulary": vocabulary, "content": data.get("content", {})}

    if not node:
        node = CurriculumNode(
            unit_id=unit.id,
            title=data["title"],
            description=data.get("description"),
            order_index=data.get("order", 0),
            node_type=data.get("type", "practice"),
            target_patterns=pattern_ids,
            extra_data=extra_data,
            estimated_duration_min=5,
        )
        session.add(node)
        logger.info(f"Created Lesson: {node.title}")
    else:
        node.description = data.get("description", node.description)
        node.order_index = data.get("order", node.order_index)
        node.extra_data = extra_data
        node.target_patterns = pattern_ids
        logger.info(f"Updated Lesson: {node.title}")


async def process_file(session: AsyncSession, file_path: Path, language: str):
    """Process a single YAML file."""
    logger.info(f"Processing {file_path.name}...")
    with open(file_path) as f:
        data = yaml.safe_load(f)

    if not data:
        return

    section = await get_or_create_section(session, data["section"], language)
    unit = await get_or_create_unit(session, section, data["unit"])

    for lesson_data in data.get("lessons", []):
        await ingest_lesson(session, unit, lesson_data, language)


async def main(language: str = "ru"):
    """Main entry point."""
    lessons_dirs = get_lessons_dirs(language)
    if not lessons_dirs:
        logger.error(f"No lesson directories found for language: {language}")
        return

    async with get_db_session() as session:
        for lessons_dir in lessons_dirs:
            logger.info(f"Processing unit: {lessons_dir.parent.name}")
            files = sorted(lessons_dir.glob("*.yaml"))
            for file_path in files:
                await process_file(session, file_path, language)

        await session.commit()
        logger.info(f"Ingestion complete for language: {language}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest lesson content from YAML files")
    parser.add_argument("--language", "-l", default="ru", help="Language code (default: ru)")
    args = parser.parse_args()
    asyncio.run(main(args.language))
