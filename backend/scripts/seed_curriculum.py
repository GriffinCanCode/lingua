#!/usr/bin/env python3
"""Seed the curriculum with Duolingo-style Russian learning path.

Each Unit contains multiple Levels (lessons):
- Level 1: Word Introduction (teaches vocabulary)
- Level 2+: Practice levels (easy → hard → review)

Run with: python3 -m scripts.seed_curriculum
"""
import asyncio
from uuid import uuid4

from sqlalchemy import delete

from core.database import get_db_session, engine, Base
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode
from ingest.vocabulary import get_vocabulary_loader


# Level type definitions with exercise distributions
LEVEL_TYPES = {
    "intro": {"name": "New Words", "duration": 3, "exercises": None},
    "easy": {"name": "Practice 1", "duration": 5, "exercises": {"multiple_choice": 8, "matching": 2}},
    "medium": {"name": "Practice 2", "duration": 5, "exercises": {"word_bank": 6, "multiple_choice": 4}},
    "hard": {"name": "Practice 3", "duration": 5, "exercises": {"typing": 5, "word_bank": 5}},
    "review": {"name": "Review", "duration": 7, "exercises": {"typing": 3, "word_bank": 4, "multiple_choice": 2, "matching": 1}},
}


def generate_unit_levels(unit_title: str, vocab_count: int) -> list[dict]:
    """Generate 3-7 lesson levels based on vocabulary count."""
    num_levels = min(7, max(3, vocab_count // 3))

    levels = [{"level": 1, "type": "intro", "title": f"{unit_title} - New Words"}]

    if num_levels >= 2:
        levels.append({"level": 2, "type": "easy", "title": f"{unit_title} - Practice 1"})
    if num_levels >= 3:
        levels.append({"level": 3, "type": "medium", "title": f"{unit_title} - Practice 2"})
    if num_levels >= 4:
        levels.append({"level": 4, "type": "hard", "title": f"{unit_title} - Practice 3"})
    if num_levels >= 5:
        levels.append({"level": 5, "type": "review", "title": f"{unit_title} - Review"})
    if num_levels >= 6:
        levels.append({"level": 6, "type": "hard", "title": f"{unit_title} - Challenge"})
    if num_levels >= 7:
        levels.append({"level": 7, "type": "review", "title": f"{unit_title} - Mastery"})

    return levels


# Curriculum structure - Units reference vocabulary sheets
CURRICULUM = {
    "sections": [
        {
            "id": "foundations",
            "title": "Foundations",
            "description": "Learn to read Cyrillic and speak your first words",
            "icon": "home",
            "color": "#58CC02",
            "units": [
                {
                    "id": "alphabet",
                    "title": "The Alphabet",
                    "description": "Read Russian through words you already know",
                    "icon": "book",
                    "vocab_unit": "unit1",
                    "vocab_lessons": ["lesson_1_cognates"],
                },
                {
                    "id": "basics1",
                    "title": "Basics 1",
                    "description": "This is, yes/no, basic questions",
                    "icon": "star",
                    "vocab_unit": "unit1",
                    "vocab_lessons": ["lesson_2_identification", "lesson_3_gender"],
                },
                {
                    "id": "basics2",
                    "title": "Basics 2",
                    "description": "Possession and question words",
                    "icon": "zap",
                    "vocab_unit": "unit1",
                    "vocab_lessons": ["lesson_4_possession", "lesson_5_questions"],
                },
            ],
        },
        {
            "id": "essentials",
            "title": "Essentials",
            "description": "Numbers, colors, food, and your first verbs",
            "icon": "layers",
            "color": "#1CB0F6",
            "units": [
                {
                    "id": "numbers",
                    "title": "Numbers",
                    "description": "Count from 1 to 10",
                    "icon": "hash",
                    "vocab_unit": "unit2",
                    "vocab_lessons": ["lesson_1_numbers"],
                },
                {
                    "id": "colors",
                    "title": "Colors",
                    "description": "Describe with colors",
                    "icon": "palette",
                    "vocab_unit": "unit2",
                    "vocab_lessons": ["lesson_2_colors"],
                },
                {
                    "id": "verbs1",
                    "title": "Verbs 1",
                    "description": "I want, I know, I love",
                    "icon": "activity",
                    "vocab_unit": "unit2",
                    "vocab_lessons": ["lesson_3_verbs"],
                },
                {
                    "id": "food",
                    "title": "Food",
                    "description": "Order at restaurants",
                    "icon": "coffee",
                    "vocab_unit": "unit2",
                    "vocab_lessons": ["lesson_4_food"],
                },
                {
                    "id": "time",
                    "title": "Time",
                    "description": "When things happen",
                    "icon": "clock",
                    "vocab_unit": "unit2",
                    "vocab_lessons": ["lesson_5_time"],
                },
            ],
        },
    ],
}


async def clear_curriculum(session):
    """Clear existing curriculum data."""
    await session.execute(delete(CurriculumNode))
    await session.execute(delete(CurriculumUnit))
    await session.execute(delete(CurriculumSection))
    await session.commit()
    print("Cleared existing curriculum")


async def create_curriculum(session):
    """Create the full curriculum structure with dynamic levels."""
    loader = get_vocabulary_loader()

    for section_idx, section_data in enumerate(CURRICULUM["sections"]):
        section = CurriculumSection(
            id=uuid4(),
            language="ru",
            title=section_data["title"],
            description=section_data["description"],
            order_index=section_idx,
            icon=section_data.get("icon"),
            color=section_data.get("color"),
        )
        session.add(section)
        await session.flush()
        print(f"Section: {section.title}")

        for unit_idx, unit_data in enumerate(section_data["units"]):
            # Count vocabulary for this unit
            vocab_count = 0
            vocab_unit_id = unit_data.get("vocab_unit")
            vocab_lessons = unit_data.get("vocab_lessons", [])

            if vocab_unit_id:
                unit_vocab = loader.load_unit(vocab_unit_id)
                if unit_vocab:
                    for lesson_key in vocab_lessons:
                        lesson = unit_vocab.by_lesson.get(lesson_key)
                        if lesson:
                            vocab_count += len(lesson.primary) + len(lesson.secondary)

            # Default vocab count if none found
            vocab_count = vocab_count or 8

            unit = CurriculumUnit(
                id=uuid4(),
                section_id=section.id,
                title=unit_data["title"],
                description=unit_data["description"],
                order_index=unit_idx,
                icon=unit_data.get("icon"),
                extra_data={
                    "vocab_unit": vocab_unit_id,
                    "vocab_lessons": vocab_lessons,
                },
            )
            session.add(unit)
            await session.flush()

            # Generate levels for this unit
            levels = generate_unit_levels(unit_data["title"], vocab_count)
            print(f"  Unit: {unit.title} ({len(levels)} levels, {vocab_count} words)")

            for level_data in levels:
                level_info = LEVEL_TYPES[level_data["type"]]
                node = CurriculumNode(
                    id=uuid4(),
                    unit_id=unit.id,
                    title=level_data["title"],
                    order_index=level_data["level"] - 1,
                    level=level_data["level"],
                    level_type=level_data["type"],
                    estimated_duration_min=level_info["duration"],
                    extra_data={
                        "vocab_unit": vocab_unit_id,
                        "vocab_lessons": vocab_lessons,
                        "exercises": level_info["exercises"],
                    },
                )
                session.add(node)
                print(f"    Level {level_data['level']}: {level_data['type']}")


async def main():
    """Run the curriculum seeder."""
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("\nSeeding curriculum with dynamic levels...")
    async with get_db_session() as session:
        await clear_curriculum(session)
        await create_curriculum(session)
        await session.commit()
        print("\n✓ Curriculum seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
