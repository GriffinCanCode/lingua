#!/usr/bin/env python3
"""Verify lesson content in the database."""
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import get_db_session
from models.curriculum import CurriculumSection, CurriculumUnit, CurriculumNode
from models.srs import Sentence

async def main():
    async with get_db_session() as session:
        # Check Section
        stmt = select(CurriculumSection).where(CurriculumSection.title == "Foundations").options(
            selectinload(CurriculumSection.units).selectinload(CurriculumUnit.nodes)
        )
        result = await session.execute(stmt)
        section = result.scalar_one_or_none()

        if not section:
            print("❌ Section 'Foundations' not found.")
            return

        print(f"✅ Section: {section.title}")
        
        for unit in section.units:
            print(f"  ✅ Unit: {unit.title}")
            for node in unit.nodes:
                print(f"    ✅ Lesson: {node.title}")
                print(f"       Type: {node.node_type}")
                print(f"       Extra Data: {node.extra_data}")
                
                # Verify sentences
                if "featured_sentences" in node.extra_data:
                    for s_id in node.extra_data["featured_sentences"]:
                        s_stmt = select(Sentence).where(Sentence.id == s_id)
                        s_res = await session.execute(s_stmt)
                        sent = s_res.scalar_one_or_none()
                        if sent:
                            print(f"       -> Sentence: {sent.text} ({sent.translation})")
                        else:
                            print(f"       ❌ Sentence ID {s_id} not found!")

if __name__ == "__main__":
    asyncio.run(main())
