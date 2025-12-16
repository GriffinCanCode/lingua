"""Russian morphological tag mappings for pymorphy3."""

# Case mappings (pymorphy3 tag -> human-readable)
CASE_MAP = {
    "nomn": "nominative",
    "gent": "genitive",
    "datv": "dative",
    "accs": "accusative",
    "ablt": "instrumental",
    "loct": "prepositional",
}
CASE_MAP_REV = {v: k for k, v in CASE_MAP.items()}

# Number mappings
NUMBER_MAP = {"sing": "singular", "plur": "plural"}
NUMBER_MAP_REV = {v: k for k, v in NUMBER_MAP.items()}

# Gender mappings
GENDER_MAP = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}
GENDER_MAP_REV = {v: k for k, v in GENDER_MAP.items()}

# Part of speech mappings
POS_MAP = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJF": "adjective",
    "ADJS": "short_adjective",
    "ADVB": "adverb",
    "PREP": "preposition",
    "CONJ": "conjunction",
    "PRCL": "particle",
    "NUMR": "numeral",
    "NPRO": "pronoun",
}

# Russian grammatical cases (ordered)
CASES = ["nominative", "genitive", "dative", "accusative", "instrumental", "prepositional"]
