"""Russian declension patterns for teaching morphology."""

# Declension pattern definitions for teaching
DECLENSION_PATTERNS = {
    "fem_a": {
        "id": "fem_a_declension",
        "name": "Feminine -а/-я",
        "description": "Feminine nouns ending in -а or -я",
        "type": "noun_declension",
        "endings": {
            "nominative": {"singular": "а", "plural": "ы"},
            "genitive": {"singular": "ы", "plural": ""},
            "dative": {"singular": "е", "plural": "ам"},
            "accusative": {"singular": "у", "plural": ""},
            "instrumental": {"singular": "ой", "plural": "ами"},
            "prepositional": {"singular": "е", "plural": "ах"},
        },
        "soft_endings": {
            "nominative": {"singular": "я", "plural": "и"},
            "genitive": {"singular": "и", "plural": "ь"},
            "dative": {"singular": "е", "plural": "ям"},
            "accusative": {"singular": "ю", "plural": "ь"},
            "instrumental": {"singular": "ей", "plural": "ями"},
            "prepositional": {"singular": "е", "plural": "ях"},
        },
    },
    "masc_hard": {
        "id": "masc_hard_declension",
        "name": "Masculine Hard",
        "description": "Masculine nouns ending in a consonant",
        "type": "noun_declension",
        "endings": {
            "nominative": {"singular": "", "plural": "ы"},
            "genitive": {"singular": "а", "plural": "ов"},
            "dative": {"singular": "у", "plural": "ам"},
            "accusative": {"singular": "", "plural": "ов"},
            "instrumental": {"singular": "ом", "plural": "ами"},
            "prepositional": {"singular": "е", "plural": "ах"},
        },
    },
    "neut_o": {
        "id": "neut_o_declension",
        "name": "Neuter -о/-е",
        "description": "Neuter nouns ending in -о or -е",
        "type": "noun_declension",
        "endings": {
            "nominative": {"singular": "о", "plural": "а"},
            "genitive": {"singular": "а", "plural": ""},
            "dative": {"singular": "у", "plural": "ам"},
            "accusative": {"singular": "о", "plural": "а"},
            "instrumental": {"singular": "ом", "plural": "ами"},
            "prepositional": {"singular": "е", "plural": "ах"},
        },
    },
}

# Common ending distractors by case for pattern exercises
ENDING_DISTRACTORS = {
    "nominative": ["а", "о", "е", "ы", "и", ""],
    "genitive": ["а", "ы", "и", "ов", "ей", ""],
    "dative": ["у", "е", "ам", "ям", ""],
    "accusative": ["а", "у", "о", "ы", ""],
    "instrumental": ["ом", "ой", "ем", "ей", "ами", "ями"],
    "prepositional": ["е", "и", "у", "ах", "ях"],
}
