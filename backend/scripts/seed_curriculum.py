#!/usr/bin/env python3
"""Seed the curriculum with Russian language learning path.

This creates a comprehensive curriculum structure for Russian covering:
- Section 1: Foundations (Cases, Basic Verb Forms)
- Section 2: Verbal System (Conjugations, Aspects)
- Section 3: Advanced Grammar (Participles, Gerunds)

Run with: python3 -m scripts.seed_curriculum
"""
import asyncio
from uuid import uuid4

from sqlalchemy import select

from core.database import get_db_session, engine, Base
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode
from models.srs import SyntacticPattern


# Pattern definitions with difficulty levels
PATTERNS = {
    # Nominative patterns
    "noun_nominative_singular_masculine": {"difficulty": 1, "features": {"case": "nominative", "number": "singular", "gender": "masculine"}},
    "noun_nominative_singular_feminine": {"difficulty": 1, "features": {"case": "nominative", "number": "singular", "gender": "feminine"}},
    "noun_nominative_singular_neuter": {"difficulty": 1, "features": {"case": "nominative", "number": "singular", "gender": "neuter"}},
    "noun_nominative_plural": {"difficulty": 2, "features": {"case": "nominative", "number": "plural"}},

    # Accusative patterns
    "noun_accusative_singular_inanimate": {"difficulty": 2, "features": {"case": "accusative", "number": "singular", "animacy": "inanimate"}},
    "noun_accusative_singular_animate": {"difficulty": 3, "features": {"case": "accusative", "number": "singular", "animacy": "animate"}},
    "noun_accusative_plural": {"difficulty": 3, "features": {"case": "accusative", "number": "plural"}},

    # Genitive patterns
    "noun_genitive_singular": {"difficulty": 4, "features": {"case": "genitive", "number": "singular"}},
    "noun_genitive_plural": {"difficulty": 5, "features": {"case": "genitive", "number": "plural"}},
    "genitive_possession": {"difficulty": 4, "features": {"case": "genitive", "usage": "possession"}},
    "genitive_quantity": {"difficulty": 5, "features": {"case": "genitive", "usage": "quantity"}},
    "genitive_prepositions": {"difficulty": 5, "features": {"case": "genitive", "usage": "preposition"}},

    # Dative patterns
    "noun_dative_singular": {"difficulty": 5, "features": {"case": "dative", "number": "singular"}},
    "noun_dative_plural": {"difficulty": 6, "features": {"case": "dative", "number": "plural"}},
    "dative_indirect_object": {"difficulty": 5, "features": {"case": "dative", "usage": "indirect_object"}},

    # Instrumental patterns
    "noun_instrumental_singular": {"difficulty": 6, "features": {"case": "instrumental", "number": "singular"}},
    "noun_instrumental_plural": {"difficulty": 6, "features": {"case": "instrumental", "number": "plural"}},
    "instrumental_with": {"difficulty": 5, "features": {"case": "instrumental", "usage": "accompaniment"}},
    "instrumental_profession": {"difficulty": 6, "features": {"case": "instrumental", "usage": "profession"}},

    # Prepositional patterns
    "noun_prepositional_singular": {"difficulty": 4, "features": {"case": "prepositional", "number": "singular"}},
    "noun_prepositional_plural": {"difficulty": 5, "features": {"case": "prepositional", "number": "plural"}},
    "prepositional_location": {"difficulty": 4, "features": {"case": "prepositional", "usage": "location"}},

    # Verb patterns
    "verb_present_1st_singular": {"difficulty": 3, "features": {"tense": "present", "person": "1st", "number": "singular"}},
    "verb_present_2nd_singular": {"difficulty": 3, "features": {"tense": "present", "person": "2nd", "number": "singular"}},
    "verb_present_3rd_singular": {"difficulty": 3, "features": {"tense": "present", "person": "3rd", "number": "singular"}},
    "verb_present_1st_plural": {"difficulty": 3, "features": {"tense": "present", "person": "1st", "number": "plural"}},
    "verb_present_2nd_plural": {"difficulty": 3, "features": {"tense": "present", "person": "2nd", "number": "plural"}},
    "verb_present_3rd_plural": {"difficulty": 3, "features": {"tense": "present", "person": "3rd", "number": "plural"}},

    "verb_past_masculine": {"difficulty": 4, "features": {"tense": "past", "gender": "masculine"}},
    "verb_past_feminine": {"difficulty": 4, "features": {"tense": "past", "gender": "feminine"}},
    "verb_past_neuter": {"difficulty": 4, "features": {"tense": "past", "gender": "neuter"}},
    "verb_past_plural": {"difficulty": 4, "features": {"tense": "past", "number": "plural"}},

    "verb_future_imperfective": {"difficulty": 5, "features": {"tense": "future", "aspect": "imperfective"}},
    "verb_future_perfective": {"difficulty": 5, "features": {"tense": "future", "aspect": "perfective"}},

    "verb_imperative_singular": {"difficulty": 5, "features": {"mood": "imperative", "number": "singular"}},
    "verb_imperative_plural": {"difficulty": 5, "features": {"mood": "imperative", "number": "plural"}},

    # Adjective patterns
    "adjective_nominative_masculine": {"difficulty": 3, "features": {"pos": "adjective", "case": "nominative", "gender": "masculine"}},
    "adjective_nominative_feminine": {"difficulty": 3, "features": {"pos": "adjective", "case": "nominative", "gender": "feminine"}},
    "adjective_nominative_neuter": {"difficulty": 3, "features": {"pos": "adjective", "case": "nominative", "gender": "neuter"}},
    "adjective_agreement": {"difficulty": 4, "features": {"pos": "adjective", "usage": "agreement"}},

    # Pronoun patterns
    "pronoun_personal_nominative": {"difficulty": 2, "features": {"pos": "pronoun", "case": "nominative"}},
    "pronoun_personal_accusative": {"difficulty": 3, "features": {"pos": "pronoun", "case": "accusative"}},
    "pronoun_personal_genitive": {"difficulty": 4, "features": {"pos": "pronoun", "case": "genitive"}},
    "pronoun_personal_dative": {"difficulty": 5, "features": {"pos": "pronoun", "case": "dative"}},
}


# Curriculum structure
CURRICULUM = {
    "sections": [
        {
            "title": "Foundations",
            "description": "Master the building blocks: basic noun cases and sentence structure",
            "icon": "foundation",
            "color": "#3B82F6",
            "units": [
                {
                    "title": "Nominative Case",
                    "description": "The subject form - who or what does the action",
                    "icon": "person",
                    "nodes": [
                        {"title": "Singular Nouns", "type": "introduction", "patterns": ["noun_nominative_singular_masculine", "noun_nominative_singular_feminine", "noun_nominative_singular_neuter"], "complexity": (1, 3), "duration": 5},
                        {"title": "Masculine Nouns", "type": "practice", "patterns": ["noun_nominative_singular_masculine"], "complexity": (1, 3), "duration": 5},
                        {"title": "Feminine Nouns", "type": "practice", "patterns": ["noun_nominative_singular_feminine"], "complexity": (1, 3), "duration": 5},
                        {"title": "Neuter Nouns", "type": "practice", "patterns": ["noun_nominative_singular_neuter"], "complexity": (1, 3), "duration": 5},
                        {"title": "Plural Forms", "type": "practice", "patterns": ["noun_nominative_plural"], "complexity": (1, 4), "duration": 5},
                        {"title": "Mixed Practice", "type": "mixed", "patterns": ["noun_nominative_singular_masculine", "noun_nominative_singular_feminine", "noun_nominative_singular_neuter", "noun_nominative_plural"], "complexity": (1, 4), "duration": 10},
                    ],
                },
                {
                    "title": "Personal Pronouns",
                    "description": "I, you, he, she, we, they in Russian",
                    "icon": "users",
                    "nodes": [
                        {"title": "Subject Pronouns", "type": "introduction", "patterns": ["pronoun_personal_nominative"], "complexity": (1, 2), "duration": 5},
                        {"title": "Using я, ты, он/она", "type": "practice", "patterns": ["pronoun_personal_nominative"], "complexity": (1, 3), "duration": 5},
                        {"title": "Plural Pronouns", "type": "practice", "patterns": ["pronoun_personal_nominative"], "complexity": (1, 3), "duration": 5},
                    ],
                },
                {
                    "title": "Accusative Case",
                    "description": "The direct object - what the action affects",
                    "icon": "target",
                    "nodes": [
                        {"title": "Inanimate Objects", "type": "introduction", "patterns": ["noun_accusative_singular_inanimate"], "complexity": (2, 4), "duration": 5},
                        {"title": "Animate Objects", "type": "practice", "patterns": ["noun_accusative_singular_animate"], "complexity": (2, 5), "duration": 5},
                        {"title": "Plural Accusative", "type": "practice", "patterns": ["noun_accusative_plural"], "complexity": (3, 5), "duration": 5},
                        {"title": "Nom vs Acc Discrimination", "type": "mixed", "patterns": ["noun_nominative_singular_masculine", "noun_accusative_singular_inanimate", "noun_accusative_singular_animate"], "complexity": (2, 5), "duration": 10},
                    ],
                },
                {
                    "title": "Basic Adjectives",
                    "description": "Describing nouns - colors, sizes, qualities",
                    "icon": "palette",
                    "nodes": [
                        {"title": "Adjective Forms", "type": "introduction", "patterns": ["adjective_nominative_masculine", "adjective_nominative_feminine", "adjective_nominative_neuter"], "complexity": (2, 4), "duration": 5},
                        {"title": "Adjective Agreement", "type": "practice", "patterns": ["adjective_agreement"], "complexity": (3, 5), "duration": 5},
                        {"title": "Noun + Adjective Combos", "type": "mixed", "patterns": ["adjective_nominative_masculine", "adjective_nominative_feminine", "noun_nominative_singular_masculine", "noun_nominative_singular_feminine"], "complexity": (2, 5), "duration": 10},
                    ],
                },
                {
                    "title": "Foundations Checkpoint",
                    "description": "Review everything from Section 1",
                    "icon": "check",
                    "is_checkpoint": True,
                    "nodes": [
                        {"title": "Section 1 Review", "type": "checkpoint", "patterns": ["noun_nominative_singular_masculine", "noun_nominative_singular_feminine", "noun_accusative_singular_inanimate", "adjective_nominative_masculine"], "complexity": (1, 5), "duration": 15},
                    ],
                },
            ],
        },
        {
            "title": "Case System",
            "description": "Master all six Russian cases for complete noun mastery",
            "icon": "layers",
            "color": "#8B5CF6",
            "units": [
                {
                    "title": "Genitive Case - Basics",
                    "description": "Possession, absence, and quantity",
                    "icon": "package",
                    "nodes": [
                        {"title": "Singular Genitive", "type": "introduction", "patterns": ["noun_genitive_singular"], "complexity": (3, 5), "duration": 5},
                        {"title": "Possession (у меня есть)", "type": "practice", "patterns": ["genitive_possession"], "complexity": (3, 5), "duration": 5},
                        {"title": "Plural Genitive", "type": "practice", "patterns": ["noun_genitive_plural"], "complexity": (4, 6), "duration": 5},
                        {"title": "Quantities & Numbers", "type": "practice", "patterns": ["genitive_quantity"], "complexity": (4, 6), "duration": 5},
                    ],
                },
                {
                    "title": "Genitive with Prepositions",
                    "description": "из, от, для, без, до, после and more",
                    "icon": "arrow-right",
                    "nodes": [
                        {"title": "Common Prepositions", "type": "introduction", "patterns": ["genitive_prepositions"], "complexity": (4, 6), "duration": 5},
                        {"title": "Motion Prepositions", "type": "practice", "patterns": ["genitive_prepositions"], "complexity": (4, 6), "duration": 5},
                        {"title": "Mixed Genitive Practice", "type": "mixed", "patterns": ["noun_genitive_singular", "noun_genitive_plural", "genitive_prepositions"], "complexity": (4, 7), "duration": 10},
                    ],
                },
                {
                    "title": "Dative Case",
                    "description": "Indirect objects - to whom, for whom",
                    "icon": "gift",
                    "nodes": [
                        {"title": "Singular Dative", "type": "introduction", "patterns": ["noun_dative_singular"], "complexity": (4, 6), "duration": 5},
                        {"title": "Giving & Telling", "type": "practice", "patterns": ["dative_indirect_object"], "complexity": (4, 6), "duration": 5},
                        {"title": "Plural Dative", "type": "practice", "patterns": ["noun_dative_plural"], "complexity": (5, 7), "duration": 5},
                        {"title": "Dative Pronouns", "type": "practice", "patterns": ["pronoun_personal_dative"], "complexity": (4, 6), "duration": 5},
                    ],
                },
                {
                    "title": "Instrumental Case",
                    "description": "With what, by means of, as what",
                    "icon": "tool",
                    "nodes": [
                        {"title": "Singular Instrumental", "type": "introduction", "patterns": ["noun_instrumental_singular"], "complexity": (5, 7), "duration": 5},
                        {"title": "With (с + instrumental)", "type": "practice", "patterns": ["instrumental_with"], "complexity": (5, 7), "duration": 5},
                        {"title": "Professions (быть + inst)", "type": "practice", "patterns": ["instrumental_profession"], "complexity": (5, 7), "duration": 5},
                        {"title": "Plural Instrumental", "type": "practice", "patterns": ["noun_instrumental_plural"], "complexity": (5, 7), "duration": 5},
                    ],
                },
                {
                    "title": "Prepositional Case",
                    "description": "Location and topic - where, about what",
                    "icon": "map-pin",
                    "nodes": [
                        {"title": "Singular Prepositional", "type": "introduction", "patterns": ["noun_prepositional_singular"], "complexity": (3, 5), "duration": 5},
                        {"title": "Location (в, на)", "type": "practice", "patterns": ["prepositional_location"], "complexity": (3, 5), "duration": 5},
                        {"title": "Plural Prepositional", "type": "practice", "patterns": ["noun_prepositional_plural"], "complexity": (4, 6), "duration": 5},
                    ],
                },
                {
                    "title": "Case System Checkpoint",
                    "description": "Master all cases discrimination",
                    "icon": "trophy",
                    "is_checkpoint": True,
                    "nodes": [
                        {"title": "All Cases Review", "type": "checkpoint", "patterns": ["noun_genitive_singular", "noun_dative_singular", "noun_instrumental_singular", "noun_prepositional_singular"], "complexity": (4, 8), "duration": 15},
                    ],
                },
            ],
        },
        {
            "title": "Verbal System",
            "description": "Master Russian verb conjugation, tenses, and aspects",
            "icon": "activity",
            "color": "#10B981",
            "units": [
                {
                    "title": "Present Tense",
                    "description": "Actions happening now - I read, you speak",
                    "icon": "clock",
                    "nodes": [
                        {"title": "1st Person Forms", "type": "introduction", "patterns": ["verb_present_1st_singular", "verb_present_1st_plural"], "complexity": (2, 4), "duration": 5},
                        {"title": "2nd Person Forms", "type": "practice", "patterns": ["verb_present_2nd_singular", "verb_present_2nd_plural"], "complexity": (2, 4), "duration": 5},
                        {"title": "3rd Person Forms", "type": "practice", "patterns": ["verb_present_3rd_singular", "verb_present_3rd_plural"], "complexity": (2, 4), "duration": 5},
                        {"title": "Full Conjugation", "type": "mixed", "patterns": ["verb_present_1st_singular", "verb_present_2nd_singular", "verb_present_3rd_singular", "verb_present_1st_plural", "verb_present_2nd_plural", "verb_present_3rd_plural"], "complexity": (2, 5), "duration": 10},
                    ],
                },
                {
                    "title": "Past Tense",
                    "description": "Actions in the past - he read, she spoke",
                    "icon": "rewind",
                    "nodes": [
                        {"title": "Gender Agreement", "type": "introduction", "patterns": ["verb_past_masculine", "verb_past_feminine", "verb_past_neuter"], "complexity": (3, 5), "duration": 5},
                        {"title": "Masculine Past", "type": "practice", "patterns": ["verb_past_masculine"], "complexity": (3, 5), "duration": 5},
                        {"title": "Feminine Past", "type": "practice", "patterns": ["verb_past_feminine"], "complexity": (3, 5), "duration": 5},
                        {"title": "Plural Past", "type": "practice", "patterns": ["verb_past_plural"], "complexity": (3, 5), "duration": 5},
                    ],
                },
                {
                    "title": "Future Tense",
                    "description": "Actions to come - will read, will speak",
                    "icon": "fast-forward",
                    "nodes": [
                        {"title": "Imperfective Future", "type": "introduction", "patterns": ["verb_future_imperfective"], "complexity": (4, 6), "duration": 5},
                        {"title": "Perfective Future", "type": "practice", "patterns": ["verb_future_perfective"], "complexity": (4, 6), "duration": 5},
                        {"title": "Future Tense Practice", "type": "mixed", "patterns": ["verb_future_imperfective", "verb_future_perfective"], "complexity": (4, 7), "duration": 10},
                    ],
                },
                {
                    "title": "Imperative Mood",
                    "description": "Commands - read! speak! don't do that!",
                    "icon": "alert-triangle",
                    "nodes": [
                        {"title": "Singular Commands", "type": "introduction", "patterns": ["verb_imperative_singular"], "complexity": (4, 6), "duration": 5},
                        {"title": "Plural/Formal Commands", "type": "practice", "patterns": ["verb_imperative_plural"], "complexity": (4, 6), "duration": 5},
                        {"title": "Imperative Practice", "type": "mixed", "patterns": ["verb_imperative_singular", "verb_imperative_plural"], "complexity": (4, 7), "duration": 10},
                    ],
                },
                {
                    "title": "Verbal System Checkpoint",
                    "description": "Full verb mastery review",
                    "icon": "award",
                    "is_checkpoint": True,
                    "nodes": [
                        {"title": "All Tenses Review", "type": "checkpoint", "patterns": ["verb_present_1st_singular", "verb_past_masculine", "verb_future_perfective", "verb_imperative_singular"], "complexity": (3, 8), "duration": 15},
                    ],
                },
            ],
        },
    ],
}


async def create_patterns(session) -> dict[str, "SyntacticPattern"]:
    """Create all syntactic patterns and return mapping."""
    pattern_map = {}

    for pattern_type, config in PATTERNS.items():
        # Check if exists
        result = await session.execute(
            select(SyntacticPattern).where(
                SyntacticPattern.pattern_type == pattern_type,
                SyntacticPattern.language == "ru",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            pattern_map[pattern_type] = existing
        else:
            pattern = SyntacticPattern(
                pattern_type=pattern_type,
                language="ru",
                features=config["features"],
                difficulty=config["difficulty"],
                description=f"Pattern: {pattern_type.replace('_', ' ')}",
            )
            session.add(pattern)
            await session.flush()
            pattern_map[pattern_type] = pattern

    return pattern_map


async def create_curriculum(session, pattern_map: dict[str, "SyntacticPattern"]):
    """Create the full curriculum structure."""
    for section_idx, section_data in enumerate(CURRICULUM["sections"]):
        # Check if section exists
        result = await session.execute(
            select(CurriculumSection).where(
                CurriculumSection.title == section_data["title"],
                CurriculumSection.language == "ru",
            )
        )
        section = result.scalar_one_or_none()

        if not section:
            section = CurriculumSection(
                language="ru",
                title=section_data["title"],
                description=section_data["description"],
                order_index=section_idx,
                icon=section_data.get("icon"),
                color=section_data.get("color"),
            )
            session.add(section)
            await session.flush()
            print(f"Created section: {section.title}")
        else:
            print(f"Section exists: {section.title}")

        for unit_idx, unit_data in enumerate(section_data["units"]):
            # Check if unit exists
            result = await session.execute(
                select(CurriculumUnit).where(
                    CurriculumUnit.section_id == section.id,
                    CurriculumUnit.title == unit_data["title"],
                )
            )
            unit = result.scalar_one_or_none()

            if not unit:
                unit = CurriculumUnit(
                    section_id=section.id,
                    title=unit_data["title"],
                    description=unit_data["description"],
                    order_index=unit_idx,
                    icon=unit_data.get("icon"),
                    is_checkpoint=unit_data.get("is_checkpoint", False),
                    target_patterns=[
                        str(pattern_map[p].id)
                        for node in unit_data["nodes"]
                        for p in node["patterns"]
                        if p in pattern_map
                    ],
                )
                session.add(unit)
                await session.flush()
                print(f"  Created unit: {unit.title}")
            else:
                print(f"  Unit exists: {unit.title}")

            for node_idx, node_data in enumerate(unit_data["nodes"]):
                # Check if node exists
                result = await session.execute(
                    select(CurriculumNode).where(
                        CurriculumNode.unit_id == unit.id,
                        CurriculumNode.title == node_data["title"],
                    )
                )
                node = result.scalar_one_or_none()

                if not node:
                    complexity_min, complexity_max = node_data["complexity"]
                    node = CurriculumNode(
                        unit_id=unit.id,
                        title=node_data["title"],
                        order_index=node_idx,
                        node_type=node_data["type"],
                        target_patterns=[
                            str(pattern_map[p].id)
                            for p in node_data["patterns"]
                            if p in pattern_map
                        ],
                        complexity_min=complexity_min,
                        complexity_max=complexity_max,
                        estimated_duration_min=node_data["duration"],
                    )
                    session.add(node)
                    print(f"    Created node: {node.title}")
                else:
                    print(f"    Node exists: {node.title}")


async def main():
    """Run the curriculum seeder."""
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("\nSeeding curriculum...")
    async with get_db_session() as session:
        # Create patterns first
        print("\nCreating patterns...")
        pattern_map = await create_patterns(session)
        print(f"Created/found {len(pattern_map)} patterns")

        # Create curriculum structure
        print("\nCreating curriculum structure...")
        await create_curriculum(session, pattern_map)

        await session.commit()
        print("\n✓ Curriculum seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())

