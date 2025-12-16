from pathlib import Path
import logging
import argparse
import yaml
import asyncio
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content"

LANGUAGE_NAMES = {"ru": "Russian", "es": "Spanish", "fr": "French", "de": "German"}


def get_lessons_dirs(language: str) -> list[Path]:
    """Get all lesson directories for a language (one per unit)."""
    lang_dir = CONTENT_DIR / language
    if not lang_dir.exists():
        return []
    return sorted([d / "lessons" for d in lang_dir.iterdir() if d.is_dir() and (d / "lessons").exists()])


def unit_name_from_dir(dir_name: str) -> str:
    """Convert directory name to display name: unit_one -> Unit 1."""
    numbers = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
    parts = dir_name.split("_")
    if len(parts) == 2 and parts[0].lower() == "unit":
        num = numbers.get(parts[1].lower(), parts[1].capitalize())
        return f"Unit {num}"
    return dir_name.replace("_", " ").title()


async def get_or_create_section(session: AsyncSession, language: str) -> CurriculumSection:
    """Get or create a curriculum section for the language."""
    title = LANGUAGE_NAMES.get(language, language.upper())
    stmt = select(CurriculumSection).where(CurriculumSection.title == title, CurriculumSection.language == language)
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        section = CurriculumSection(title=title, description=f"{title} language curriculum", order_index=0, language=language)
        session.add(section)
        await session.flush()
        logger.info(f"Created Section: {section.title}")

    return section


async def get_or_create_unit(session: AsyncSession, section: CurriculumSection, unit_dir_name: str, order: int) -> CurriculumUnit:
    """Get or create a curriculum unit."""
    title = unit_name_from_dir(unit_dir_name)
    stmt = select(CurriculumUnit).where(CurriculumUnit.section_id == section.id, CurriculumUnit.title == title)
    result = await session.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        unit = CurriculumUnit(section_id=section.id, title=title, order_index=order, prerequisite_units=[], target_patterns=[])
        session.add(unit)
        await session.flush()
        logger.info(f"Created Unit: {unit.title}")

    return unit


def extract_order_from_filename(filename: str) -> int:
    """Extract lesson order from filename: 00_stress.yaml -> 0."""
    match = re.match(r"(\d+)", filename)
    return int(match.group(1)) if match else 0


async def ingest_lesson(session: AsyncSession, unit: CurriculumUnit, file_path: Path):
    """Ingest a single lesson file."""
    with open(file_path) as f:
        data = yaml.safe_load(f)

    if not data or "lesson" not in data:
        logger.warning(f"Skipping {file_path.name}: no lesson data")
        return

    lesson = data["lesson"]
    title = lesson.get("title", file_path.stem)
    order = extract_order_from_filename(file_path.name)

    stmt = select(CurriculumNode).where(CurriculumNode.unit_id == unit.id, CurriculumNode.title == title)
    result = await session.execute(stmt)
    node = result.scalar_one_or_none()

    extra_data = {
        "lesson_id": lesson.get("id"),
        "subtitle": lesson.get("subtitle"),
        "icon": lesson.get("icon"),
        "duration": lesson.get("duration"),
        "lesson_type": lesson.get("type"),
        "modules": data.get("modules", []),
        "vocab_filter": data.get("vocab_filter", {}),
        "metadata": data.get("metadata", {}),
    }

    level_type = lesson.get("type", "medium")
    if level_type == "foundational":
        level_type = "intro"

    if not node:
        node = CurriculumNode(
            unit_id=unit.id,
            title=title,
            description=lesson.get("subtitle"),
            order_index=order,
            level=order + 1,
            level_type=level_type,
            estimated_duration_min=int(lesson.get("duration", "5").split()[0]) if lesson.get("duration") else 5,
            extra_data=extra_data,
        )
        session.add(node)
        logger.info(f"Created Lesson: {node.title}")
    else:
        node.description = lesson.get("subtitle", node.description)
        node.order_index = order
        node.level_type = level_type
        node.extra_data = extra_data
        logger.info(f"Updated Lesson: {node.title}")


async def main(language: str = "ru"):
    """Main entry point."""
    lessons_dirs = get_lessons_dirs(language)
    if not lessons_dirs:
        logger.error(f"No lesson directories found for language: {language}")
        return

    async with get_db_session() as session:
        section = await get_or_create_section(session, language)

        for unit_order, lessons_dir in enumerate(lessons_dirs):
            unit_name = lessons_dir.parent.name
            logger.info(f"Processing unit: {unit_name}")

            unit = await get_or_create_unit(session, section, unit_name, unit_order)

            for file_path in sorted(lessons_dir.glob("*.yaml")):
                await ingest_lesson(session, unit, file_path)

        await session.commit()
        logger.info(f"Ingestion complete for language: {language}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest lesson content from YAML files")
    parser.add_argument("--language", "-l", default="ru", help="Language code (default: ru)")
    args = parser.parse_args()
    asyncio.run(main(args.language))
