#!/usr/bin/env python3
"""Download data sources for Lingua language learning platform.

Downloads:
- Universal Dependencies Russian corpora
- Tatoeba sentence pairs
- OpenRussian word list (bonus)

Run with: python3 -m scripts.download_data [--all | --ud | --tatoeba | --openrussian]
"""
import argparse
import os
import sys
import tarfile
import bz2
import gzip
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sources"

SOURCES = {
    "ud_syntagrus": {
        "name": "Universal Dependencies - SynTagRus",
        "url": "https://github.com/UniversalDependencies/UD_Russian-SynTagRus/archive/refs/heads/master.zip",
        "description": "Large Russian corpus with ~60K annotated sentences",
        "license": "CC-BY-SA-4.0",
    },
    "ud_taiga": {
        "name": "Universal Dependencies - Taiga",
        "url": "https://github.com/UniversalDependencies/UD_Russian-Taiga/archive/refs/heads/master.zip",
        "description": "Russian web corpus with ~20K sentences",
        "license": "CC-BY-SA-4.0",
    },
    "ud_gsd": {
        "name": "Universal Dependencies - GSD",
        "url": "https://github.com/UniversalDependencies/UD_Russian-GSD/archive/refs/heads/master.zip",
        "description": "Google's Russian treebank",
        "license": "CC-BY-SA-4.0",
    },
    "tatoeba_sentences": {
        "name": "Tatoeba Sentences",
        "url": "https://downloads.tatoeba.org/exports/sentences.tar.bz2",
        "description": "All Tatoeba sentences with language tags",
        "license": "CC-BY-2.0",
    },
    "tatoeba_links": {
        "name": "Tatoeba Links",
        "url": "https://downloads.tatoeba.org/exports/links.tar.bz2",
        "description": "Translation links between sentences",
        "license": "CC-BY-2.0",
    },
    "openrussian": {
        "name": "OpenRussian Dictionary",
        "url": "https://github.com/Badestrand/russian-dictionary/raw/master/dist/openrussian-csv.zip",
        "description": "Russian words with stress marks and translations",
        "license": "CC-BY-SA-4.0",
    },
}


def download_with_progress(url: str, dest: Path) -> bool:
    """Download a file with progress indicator."""
    print(f"  Downloading: {url}")
    print(f"  Destination: {dest}")

    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 // total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(f"\r  Progress: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
                sys.stdout.flush()

        urlretrieve(url, dest, reporthook=progress)
        print()  # New line after progress
        return True

    except URLError as e:
        print(f"\n  Error downloading: {e}")
        return False


def extract_archive(archive_path: Path, dest_dir: Path) -> bool:
    """Extract archive based on file extension."""
    print(f"  Extracting: {archive_path.name}")

    try:
        if archive_path.suffix == ".zip":
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(dest_dir)

        elif archive_path.name.endswith(".tar.bz2"):
            with tarfile.open(archive_path, "r:bz2") as tf:
                tf.extractall(dest_dir)

        elif archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(dest_dir)

        elif archive_path.suffix == ".bz2":
            dest_file = dest_dir / archive_path.stem
            with bz2.open(archive_path, 'rb') as src, open(dest_file, 'wb') as dst:
                dst.write(src.read())

        elif archive_path.suffix == ".gz":
            dest_file = dest_dir / archive_path.stem
            with gzip.open(archive_path, 'rb') as src, open(dest_file, 'wb') as dst:
                dst.write(src.read())

        else:
            print(f"  Unknown archive format: {archive_path.suffix}")
            return False

        print("  Extraction complete")
        return True

    except Exception as e:
        print(f"  Error extracting: {e}")
        return False


def download_source(key: str, source: dict, force: bool = False) -> bool:
    """Download and extract a single data source."""
    print(f"\n{'='*60}")
    print(f"Source: {source['name']}")
    print(f"Description: {source['description']}")
    print(f"License: {source['license']}")
    print(f"{'='*60}")

    # Create destination directory
    dest_dir = DATA_DIR / key
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine archive filename from URL
    url = source["url"]
    archive_name = url.split("/")[-1]
    archive_path = dest_dir / archive_name

    # Check if already downloaded
    if archive_path.exists() and not force:
        print(f"  Archive already exists: {archive_path}")
        print("  Use --force to re-download")
        return True

    # Download
    if not download_with_progress(url, archive_path):
        return False

    # Extract
    if not extract_archive(archive_path, dest_dir):
        return False

    print(f"  ✓ {source['name']} ready at: {dest_dir}")
    return True


def download_ud(force: bool = False) -> bool:
    """Download all Universal Dependencies corpora."""
    success = True
    for key in ["ud_syntagrus", "ud_taiga", "ud_gsd"]:
        if not download_source(key, SOURCES[key], force):
            success = False
    return success


def download_tatoeba(force: bool = False) -> bool:
    """Download Tatoeba sentence pairs."""
    success = True
    for key in ["tatoeba_sentences", "tatoeba_links"]:
        if not download_source(key, SOURCES[key], force):
            success = False
    return success


def download_openrussian(force: bool = False) -> bool:
    """Download OpenRussian dictionary."""
    return download_source("openrussian", SOURCES["openrussian"], force)


def list_sources():
    """List all available data sources."""
    print("\nAvailable Data Sources:")
    print("=" * 60)
    for key, source in SOURCES.items():
        print(f"\n{key}:")
        print(f"  Name: {source['name']}")
        print(f"  Description: {source['description']}")
        print(f"  License: {source['license']}")
        print(f"  URL: {source['url']}")


def main():
    parser = argparse.ArgumentParser(
        description="Download data sources for Lingua language learning platform"
    )
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--ud", action="store_true", help="Download Universal Dependencies corpora")
    parser.add_argument("--tatoeba", action="store_true", help="Download Tatoeba sentence pairs")
    parser.add_argument("--openrussian", action="store_true", help="Download OpenRussian dictionary")
    parser.add_argument("--list", action="store_true", help="List available sources")
    parser.add_argument("--force", action="store_true", help="Force re-download existing files")

    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    if not any([args.all, args.ud, args.tatoeba, args.openrussian]):
        print("No sources specified. Use --help for options or --list to see available sources.")
        parser.print_help()
        return

    print(f"Data directory: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    success = True

    if args.all or args.ud:
        if not download_ud(args.force):
            success = False

    if args.all or args.tatoeba:
        if not download_tatoeba(args.force):
            success = False

    if args.all or args.openrussian:
        if not download_openrussian(args.force):
            success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ All downloads completed successfully!")
        print(f"\nData location: {DATA_DIR}")
        print("\nNext steps:")
        print("1. Run migration: cd backend && alembic upgrade head")
        print("2. Seed curriculum: python3 -m scripts.seed_curriculum")
        print("3. Ingest data: python3 -m scripts.ingest_all")
    else:
        print("✗ Some downloads failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

