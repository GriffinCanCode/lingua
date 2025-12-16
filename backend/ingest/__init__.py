"""Data Ingestion Package

Provides parsers and utilities for ingesting data from:
- Universal Dependencies (CoNLL-U format)
- Wiktionary dumps
- Tatoeba sentence pairs
"""
from ingest.parsers.conllu import CoNLLUParser, UDSentence, UDToken
from ingest.parsers.wiktionary import WiktionaryParser, WiktionaryEntry
from ingest.parsers.tatoeba import TatoebaParser, SentencePair
from ingest.pipeline import IngestionPipeline
from ingest.complexity import ComplexityScorer

__all__ = [
    "CoNLLUParser", "UDSentence", "UDToken",
    "WiktionaryParser", "WiktionaryEntry",
    "TatoebaParser", "SentencePair",
    "IngestionPipeline", "ComplexityScorer",
]
