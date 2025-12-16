#!/usr/bin/env python3
"""Run full data ingestion pipeline with rich visual feedback.

Ingests data from:
1. Universal Dependencies corpora → Sentences + Patterns
2. Tatoeba → Translations
3. (Optional) Wiktionary → Lemmas + Inflections

Run with: python3 -m scripts.ingest_all [--ud] [--tatoeba] [--all]
"""
# Suppress SQL logging BEFORE any imports
import os
os.environ["LOG_SQL"] = "false"

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import timedelta

# Ensure SQLAlchemy is quiet
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)

from ingest.pipeline import IngestionPipeline, IngestionStats


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sources"

# ANSI color codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_CYAN = "\033[36m"
C_RED = "\033[31m"


def fmt_num(n: int) -> str:
    """Format number with thousands separator."""
    return f"{n:,}"


def fmt_duration(seconds: float) -> str:
    """Format duration nicely."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return str(timedelta(seconds=int(seconds)))


def fmt_rate(count: int, seconds: float) -> str:
    """Format processing rate."""
    if seconds <= 0:
        return "∞"
    rate = count / seconds
    if rate >= 1000:
        return f"{rate/1000:.1f}K/s"
    return f"{rate:.1f}/s"


def progress_bar(current: int, total: int, width: int = 30) -> str:
    """Create a progress bar string."""
    if total <= 0:
        return f"[{'?' * width}]"
    pct = min(1.0, current / total)
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct*100:5.1f}%"


def print_header(title: str) -> None:
    """Print a section header."""
    print()
    print(f"{C_BOLD}{C_CYAN}{'═' * 60}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  {title}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}{'═' * 60}{C_RESET}")


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{C_BOLD}{C_BLUE}▶ {title}{C_RESET}")
    print(f"{C_DIM}{'─' * 50}{C_RESET}")


def print_stats(stats: IngestionStats, duration: float) -> None:
    """Print final statistics for an ingestion run."""
    print(f"\n{C_BOLD}  Results:{C_RESET}")
    print(f"    {C_GREEN}✓ Created:{C_RESET}   {fmt_num(stats.records_created):>10}")
    print(f"    {C_YELLOW}↻ Updated:{C_RESET}   {fmt_num(stats.records_updated):>10}")
    print(f"    {C_DIM}○ Skipped:{C_RESET}   {fmt_num(stats.records_skipped):>10}")
    if stats.records_failed > 0:
        print(f"    {C_RED}✗ Failed:{C_RESET}    {fmt_num(stats.records_failed):>10}")
    print(f"    {C_BOLD}━ Total:{C_RESET}     {fmt_num(stats.records_processed):>10}")
    print()
    print(f"  {C_DIM}Duration: {fmt_duration(duration)} • Rate: {fmt_rate(stats.records_processed, duration)}{C_RESET}")


async def ingest_ud(language: str = "ru") -> tuple[int, int, int]:
    """Ingest all Universal Dependencies corpora."""
    pipeline = IngestionPipeline(language=language)

    # Find all .conllu files
    conllu_files = []
    for ud_dir in ["ud_syntagrus", "ud_taiga", "ud_gsd"]:
        dir_path = DATA_DIR / ud_dir
        if dir_path.exists():
            conllu_files.extend(sorted(dir_path.rglob("*.conllu")))

    if not conllu_files:
        print(f"\n  {C_RED}✗ No CoNLL-U files found.{C_RESET}")
        print(f"    Run: {C_DIM}python3 -m scripts.download_data --ud{C_RESET}")
        return 0, 0, 0

    print(f"\n  {C_DIM}Found {len(conllu_files)} CoNLL-U files{C_RESET}")

    total_stats = {"processed": 0, "created": 0, "failed": 0}
    start_time = time.time()

    for idx, conllu_file in enumerate(conllu_files, 1):
        file_name = conllu_file.name
        corpus_name = conllu_file.parent.name.replace("UD_Russian-", "").replace("-master", "")
        print_subheader(f"[{idx}/{len(conllu_files)}] {corpus_name}: {file_name}")

        file_start = time.time()
        last_update = [0.0]

        async def progress(processed: int, total: int):
            now = time.time()
            if now - last_update[0] >= 0.1:  # Update max 10x/sec
                last_update[0] = now
                elapsed = now - file_start
                bar = progress_bar(processed, total)
                rate = fmt_rate(processed, elapsed)
                sys.stdout.write(f"\r    {bar} {fmt_num(processed):>8}/{fmt_num(total)} @ {rate}  ")
                sys.stdout.flush()

        try:
            stats = await pipeline.ingest_ud_corpus(conllu_file, progress_callback=progress)
            file_duration = time.time() - file_start

            # Clear progress line and print result
            sys.stdout.write("\r" + " " * 80 + "\r")
            print(f"    {C_GREEN}✓{C_RESET} {fmt_num(stats.records_created):>6} created, "
                  f"{C_DIM}{fmt_num(stats.records_skipped)} skipped{C_RESET} "
                  f"({fmt_duration(file_duration)}, {fmt_rate(stats.records_processed, file_duration)})")

            total_stats["processed"] += stats.records_processed
            total_stats["created"] += stats.records_created
            total_stats["failed"] += stats.records_failed

        except Exception as e:
            sys.stdout.write("\r" + " " * 80 + "\r")
            print(f"    {C_RED}✗ Error: {e}{C_RESET}")
            total_stats["failed"] += 1

    total_duration = time.time() - start_time
    print(f"\n{C_BOLD}  UD Ingestion Summary:{C_RESET}")
    print(f"    Total processed: {C_BOLD}{fmt_num(total_stats['processed'])}{C_RESET}")
    print(f"    Total created:   {C_GREEN}{fmt_num(total_stats['created'])}{C_RESET}")
    if total_stats['failed'] > 0:
        print(f"    Total failed:    {C_RED}{fmt_num(total_stats['failed'])}{C_RESET}")
    print(f"    Duration:        {fmt_duration(total_duration)}")
    print(f"    Avg rate:        {fmt_rate(total_stats['processed'], total_duration)}")

    return total_stats["processed"], total_stats["created"], total_stats["failed"]


async def ingest_tatoeba(language: str = "ru", target_lang: str = "en", limit: int | None = None) -> tuple[int, int, int]:
    """Ingest Tatoeba sentence pairs."""
    pipeline = IngestionPipeline(language=language)

    sentences_dir = DATA_DIR / "tatoeba_sentences"
    links_dir = DATA_DIR / "tatoeba_links"

    # Find the extracted files
    sentences_files = list(sentences_dir.rglob("sentences.csv")) + list(sentences_dir.rglob("sentences_detailed.csv"))
    links_files = list(links_dir.rglob("links.csv"))

    if not sentences_files or not links_files:
        print(f"\n  {C_RED}✗ Tatoeba files not found.{C_RESET}")
        print(f"    Run: {C_DIM}python3 -m scripts.download_data --tatoeba{C_RESET}")
        return 0, 0, 0

    sentences_path = sentences_files[0]
    links_path = links_files[0]

    print(f"\n  {C_DIM}Sentences: {sentences_path.name}{C_RESET}")
    print(f"  {C_DIM}Links:     {links_path.name}{C_RESET}")
    print(f"  {C_DIM}Languages: {language} → {target_lang}{C_RESET}")
    if limit:
        print(f"  {C_YELLOW}Limit:     {fmt_num(limit)} pairs{C_RESET}")

    start_time = time.time()
    last_update = [0.0]

    async def progress(processed: int, total: int):
        now = time.time()
        if now - last_update[0] >= 0.1:
            last_update[0] = now
            elapsed = now - start_time
            if total > 0:
                bar = progress_bar(processed, total)
                sys.stdout.write(f"\r    {bar} {fmt_num(processed):>8}/{fmt_num(total)} @ {fmt_rate(processed, elapsed)}  ")
            else:
                sys.stdout.write(f"\r    Processing... {fmt_num(processed):>8} @ {fmt_rate(processed, elapsed)}  ")
            sys.stdout.flush()

    try:
        print_subheader(f"Processing {language.upper()}-{target_lang.upper()} pairs")
        stats = await pipeline.ingest_tatoeba(
            sentences_path, links_path,
            target_lang=target_lang, limit=limit,
            progress_callback=progress,
        )
        duration = time.time() - start_time

        sys.stdout.write("\r" + " " * 80 + "\r")
        print_stats(stats, duration)
        return stats.records_processed, stats.records_created, stats.records_failed

    except Exception as e:
        sys.stdout.write("\r" + " " * 80 + "\r")
        print(f"\n  {C_RED}✗ Error: {e}{C_RESET}")
        raise


async def main():
    parser = argparse.ArgumentParser(
        description="Run data ingestion pipeline for Lingua",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m scripts.ingest_all --all              # Run everything
  python3 -m scripts.ingest_all --ud               # Only UD corpora
  python3 -m scripts.ingest_all --tatoeba          # Only Tatoeba
  python3 -m scripts.ingest_all --all --limit 1000 # Test with 1000 records
        """
    )
    parser.add_argument("--all", action="store_true", help="Run all ingestion tasks")
    parser.add_argument("--ud", action="store_true", help="Ingest Universal Dependencies")
    parser.add_argument("--tatoeba", action="store_true", help="Ingest Tatoeba translations")
    parser.add_argument("--language", default="ru", help="Target language code (default: ru)")
    parser.add_argument("--target-lang", default="en", help="Translation target language (default: en)")
    parser.add_argument("--limit", type=int, help="Limit number of records (for testing)")

    args = parser.parse_args()

    if not any([args.all, args.ud, args.tatoeba]):
        print(f"{C_YELLOW}No tasks specified. Use --help for options.{C_RESET}")
        parser.print_help()
        return

    # Header
    print()
    print(f"{C_BOLD}{C_MAGENTA}╔{'═' * 58}╗{C_RESET}")
    print(f"{C_BOLD}{C_MAGENTA}║{'LINGUA DATA INGESTION PIPELINE':^58}║{C_RESET}")
    print(f"{C_BOLD}{C_MAGENTA}╚{'═' * 58}╝{C_RESET}")
    print()
    print(f"  {C_DIM}Data directory:{C_RESET} {DATA_DIR}")
    print(f"  {C_DIM}Language:{C_RESET}       {args.language}")
    if args.limit:
        print(f"  {C_YELLOW}⚠ Limited to {fmt_num(args.limit)} records per source{C_RESET}")

    grand_start = time.time()
    totals = {"processed": 0, "created": 0, "failed": 0}

    if args.all or args.ud:
        print_header("Universal Dependencies Corpora")
        p, c, f = await ingest_ud(args.language)
        totals["processed"] += p
        totals["created"] += c
        totals["failed"] += f

    if args.all or args.tatoeba:
        print_header("Tatoeba Sentence Translations")
        p, c, f = await ingest_tatoeba(args.language, args.target_lang, args.limit)
        totals["processed"] += p
        totals["created"] += c
        totals["failed"] += f

    # Final summary
    grand_duration = time.time() - grand_start
    print()
    print(f"{C_BOLD}{C_GREEN}╔{'═' * 58}╗{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}║{'✓ INGESTION COMPLETE':^58}║{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}╚{'═' * 58}╝{C_RESET}")
    print()
    print(f"  {C_BOLD}Grand Total:{C_RESET}")
    print(f"    Records processed: {C_BOLD}{fmt_num(totals['processed'])}{C_RESET}")
    print(f"    Records created:   {C_GREEN}{fmt_num(totals['created'])}{C_RESET}")
    if totals['failed'] > 0:
        print(f"    Records failed:    {C_RED}{fmt_num(totals['failed'])}{C_RESET}")
    print(f"    Total time:        {C_CYAN}{fmt_duration(grand_duration)}{C_RESET}")
    print(f"    Overall rate:      {fmt_rate(totals['processed'], grand_duration)}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
