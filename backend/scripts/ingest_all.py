#!/usr/bin/env python3
"""Run full data ingestion pipeline.

Ingests data from:
1. Universal Dependencies corpora → Sentences + Patterns
2. Tatoeba → Translations
3. (Optional) Wiktionary → Lemmas + Inflections

Run with: python3 -m scripts.ingest_all [--ud] [--tatoeba] [--all]
"""
import argparse
import asyncio
import glob
from pathlib import Path

from ingest.pipeline import IngestionPipeline


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sources"


async def ingest_ud(language: str = "ru"):
    """Ingest all Universal Dependencies corpora."""
    pipeline = IngestionPipeline(language=language)

    # Find all .conllu files
    conllu_files = []
    for ud_dir in ["ud_syntagrus", "ud_taiga", "ud_gsd"]:
        dir_path = DATA_DIR / ud_dir
        if dir_path.exists():
            conllu_files.extend(dir_path.rglob("*.conllu"))

    if not conllu_files:
        print("No CoNLL-U files found. Run 'python3 -m scripts.download_data --ud' first.")
        return

    print(f"Found {len(conllu_files)} CoNLL-U files")

    total_stats = {"processed": 0, "created": 0, "failed": 0}

    for conllu_file in conllu_files:
        print(f"\nProcessing: {conllu_file.name}")

        async def progress(processed: int, total: int):
            if total > 0:
                print(f"  Progress: {processed}/{total} ({processed*100//total}%)", end="\r")

        try:
            stats = await pipeline.ingest_ud_corpus(conllu_file, progress_callback=progress)
            print(f"\n  ✓ Processed: {stats.records_processed}, Created: {stats.records_created}, Failed: {stats.records_failed}")

            total_stats["processed"] += stats.records_processed
            total_stats["created"] += stats.records_created
            total_stats["failed"] += stats.records_failed

        except Exception as e:
            print(f"\n  ✗ Error: {e}")
            total_stats["failed"] += 1

    print(f"\nUD Ingestion Complete:")
    print(f"  Total processed: {total_stats['processed']}")
    print(f"  Total created: {total_stats['created']}")
    print(f"  Total failed: {total_stats['failed']}")


async def ingest_tatoeba(language: str = "ru", target_lang: str = "en", limit: int | None = None):
    """Ingest Tatoeba sentence pairs."""
    pipeline = IngestionPipeline(language=language)

    sentences_dir = DATA_DIR / "tatoeba_sentences"
    links_dir = DATA_DIR / "tatoeba_links"

    # Find the extracted files
    sentences_files = list(sentences_dir.rglob("sentences.csv")) + list(sentences_dir.rglob("sentences_detailed.csv"))
    links_files = list(links_dir.rglob("links.csv"))

    if not sentences_files or not links_files:
        print("Tatoeba files not found. Run 'python3 -m scripts.download_data --tatoeba' first.")
        print(f"  Looked in: {sentences_dir} and {links_dir}")
        return

    sentences_path = sentences_files[0]
    links_path = links_files[0]

    print(f"Sentences file: {sentences_path}")
    print(f"Links file: {links_path}")
    print(f"Language pair: {language} → {target_lang}")
    if limit:
        print(f"Limit: {limit} pairs")

    async def progress(processed: int, total: int):
        if total > 0:
            print(f"  Progress: {processed}/{total}", end="\r")
        else:
            print(f"  Processed: {processed}", end="\r")

    try:
        stats = await pipeline.ingest_tatoeba(
            sentences_path,
            links_path,
            target_lang=target_lang,
            limit=limit,
            progress_callback=progress,
        )
        print(f"\n✓ Tatoeba Ingestion Complete:")
        print(f"  Processed: {stats.records_processed}")
        print(f"  Created: {stats.records_created}")
        print(f"  Updated: {stats.records_updated}")
        print(f"  Failed: {stats.records_failed}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


async def main():
    parser = argparse.ArgumentParser(
        description="Run data ingestion pipeline for Lingua"
    )
    parser.add_argument("--all", action="store_true", help="Run all ingestion tasks")
    parser.add_argument("--ud", action="store_true", help="Ingest Universal Dependencies")
    parser.add_argument("--tatoeba", action="store_true", help="Ingest Tatoeba translations")
    parser.add_argument("--language", default="ru", help="Target language code (default: ru)")
    parser.add_argument("--target-lang", default="en", help="Translation target language (default: en)")
    parser.add_argument("--limit", type=int, help="Limit number of records (for testing)")

    args = parser.parse_args()

    if not any([args.all, args.ud, args.tatoeba]):
        print("No tasks specified. Use --help for options.")
        parser.print_help()
        return

    print("=" * 60)
    print("Lingua Data Ingestion Pipeline")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Language: {args.language}")

    if args.all or args.ud:
        print("\n" + "=" * 60)
        print("Universal Dependencies Ingestion")
        print("=" * 60)
        await ingest_ud(args.language)

    if args.all or args.tatoeba:
        print("\n" + "=" * 60)
        print("Tatoeba Ingestion")
        print("=" * 60)
        await ingest_tatoeba(args.language, args.target_lang, args.limit)

    print("\n" + "=" * 60)
    print("✓ Ingestion Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

