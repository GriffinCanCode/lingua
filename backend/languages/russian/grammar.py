"""Russian grammar configuration for frontend."""
from languages.base import CaseConfig, GenderConfig, NumberConfig, GrammarConfig

# Case configurations with UI hints and colors
CASE_CONFIGS = [
    CaseConfig(
        id="nominative",
        label="Nominative",
        hint="кто? что? (who? what?)",
        color_bg="bg-blue-50",
        color_text="text-blue-700",
        color_border="border-blue-300",
    ),
    CaseConfig(
        id="genitive",
        label="Genitive",
        hint="кого? чего? (of whom? of what?)",
        color_bg="bg-green-50",
        color_text="text-green-700",
        color_border="border-green-300",
    ),
    CaseConfig(
        id="dative",
        label="Dative",
        hint="кому? чему? (to whom? to what?)",
        color_bg="bg-orange-50",
        color_text="text-orange-700",
        color_border="border-orange-300",
    ),
    CaseConfig(
        id="accusative",
        label="Accusative",
        hint="кого? что? (whom? what?)",
        color_bg="bg-purple-50",
        color_text="text-purple-700",
        color_border="border-purple-300",
    ),
    CaseConfig(
        id="instrumental",
        label="Instrumental",
        hint="кем? чем? (with whom? with what?)",
        color_bg="bg-pink-50",
        color_text="text-pink-700",
        color_border="border-pink-300",
    ),
    CaseConfig(
        id="prepositional",
        label="Prepositional",
        hint="о ком? о чём? (about whom? about what?)",
        color_bg="bg-cyan-50",
        color_text="text-cyan-700",
        color_border="border-cyan-300",
    ),
]

GENDER_CONFIGS = [
    GenderConfig(id="masculine", label="Masculine", short="m"),
    GenderConfig(id="feminine", label="Feminine", short="f"),
    GenderConfig(id="neuter", label="Neuter", short="n"),
]

NUMBER_CONFIGS = [
    NumberConfig(id="singular", label="Singular"),
    NumberConfig(id="plural", label="Plural"),
]

RUSSIAN_GRAMMAR_CONFIG = GrammarConfig(
    cases=CASE_CONFIGS,
    genders=GENDER_CONFIGS,
    numbers=NUMBER_CONFIGS,
    has_declension=True,
    has_conjugation=True,
)
