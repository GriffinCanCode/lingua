#!/usr/bin/env python3
"""Seed the curriculum from the file system.

This script reads the lesson files from data/content/ru and populates the database
with the corresponding Sections, Units, and Nodes (Lessons).

Run with: python3 -m scripts.seed_curriculum
"""
import asyncio
from pathlib import Path
from uuid import uuid4, UUID
import yaml

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session, engine, Base
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode


CONTENT_DIR = Path(__file__).parent.parent.parent / "data" / "content"

# Map folder names to Section titles (or create sections dynamically)
SECTIONS = [
    {
        "id": "section1",
        "title": "Russian Path",
        "description": "Your journey to learning Russian",
        "color": "#58CC02",
        "icon": "home",
        "units": ["unit_one", "unit_two"]  # Order of units
    }
]

async def clear_curriculum(session: AsyncSession):
    """Clear existing curriculum data."""
    await session.execute(delete(CurriculumNode))
    await session.execute(delete(CurriculumUnit))
    await session.execute(delete(CurriculumSection))
    await session.flush()
    print("Cleared existing curriculum")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


async def create_curriculum(session: AsyncSession, language: str = "ru"):
    """Create curriculum from file system."""
    lang_dir = CONTENT_DIR / language
    if not lang_dir.exists():
        print(f"No content found for language: {language}")
        return

    # Process defined sections
    for section_idx, section_def in enumerate(SECTIONS):
        section = CurriculumSection(
            id=uuid4(),
            language=language,
            title=section_def["title"],
            description=section_def["description"],
            order_index=section_idx,
            icon=section_def.get("icon"),
            color=section_def.get("color"),
        )
        session.add(section)
        await session.flush()
        print(f"Section: {section.title}")

        # Process units in this section
        for unit_idx, unit_folder_name in enumerate(section_def["units"]):
            unit_dir = lang_dir / unit_folder_name
            if not unit_dir.exists():
                print(f"  Warning: Unit folder {unit_folder_name} not found")
                continue

            # Load Unit Metadata from _meta.yaml
            vocab_dir = unit_dir / "vocab"
            unit_data = {}
            if vocab_dir.exists():
                meta_file = vocab_dir / "_meta.yaml"
                if meta_file.exists():
                    data = load_yaml(meta_file)
                    unit_data = data.get("unit", {})
            
            if not unit_data:
                # Fallback if no metadata found
                unit_data = {
                    "title": unit_folder_name.replace("_", " ").title(),
                    "description": "",
                    "id": unit_folder_name
                }

            unit = CurriculumUnit(
                id=uuid4(),
                section_id=section.id,
                title=unit_data.get("title", unit_folder_name),
                description=unit_data.get("description"),
                order_index=unit_idx,
                extra_data={"folder": unit_folder_name, "original_id": unit_data.get("id")},
            )
            session.add(unit)
            await session.flush()
            print(f"  Unit: {unit.title}")

            # Process Lessons
            lessons_dir = unit_dir / "lessons"
            if not lessons_dir.exists():
                print(f"    No lessons folder in {unit_folder_name}")
                continue

            lesson_files = sorted(lessons_dir.glob("*.yaml"))
            for lesson_idx, lesson_file in enumerate(lesson_files):
                data = load_yaml(lesson_file)
                if not data or "lesson" not in data:
                    continue
                
                lesson_info = data["lesson"]
                
                # Determine level type (default to medium/practice)
                # Could be inferred from file name or content
                level_type = "practice"
                if "intro" in lesson_file.name:
                    level_type = "intro"
                elif "review" in lesson_file.name:
                    level_type = "review"
                
                # Check for modules to count duration or complexity?
                # modules = data.get("modules", [])

                node = CurriculumNode(
                    id=uuid4(),
                    unit_id=unit.id,
                    title=lesson_info.get("title", lesson_file.stem),
                    description=lesson_info.get("subtitle"),
                    order_index=lesson_idx,
                    level=lesson_idx + 1, # Simple progression
                    level_type=level_type, # TODO: Map from lesson type
                    estimated_duration_min=5, # Default
                    extra_data={
                        "filename": lesson_file.name,
                        "original_id": lesson_info.get("id"),
                        "icon": lesson_info.get("icon")
                    }
                )
                session.add(node)
                print(f"    Lesson: {node.title}")


async def main():
    """Run the curriculum seeder."""
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("\nSeeding curriculum from file system...")
    async with get_db_session() as session:
        await clear_curriculum(session)
        await create_curriculum(session)
        await session.commit()
        print("\n✓ Curriculum seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
