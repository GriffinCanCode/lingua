"""Parser implementations for various data formats."""
from ingest.parsers.conllu import CoNLLUParser, UDSentence, UDToken
from ingest.parsers.wiktionary import WiktionaryParser, WiktionaryEntry
from ingest.parsers.tatoeba import TatoebaParser, SentencePair

__all__ = [
    "CoNLLUParser", "UDSentence", "UDToken",
    "WiktionaryParser", "WiktionaryEntry",
    "TatoebaParser", "SentencePair",
]

