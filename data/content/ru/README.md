# Russian Content

All Russian language content organized by unit.

**See [CURRICULUM.md](./CURRICULUM.md) for the complete 25-unit course outline.**

## Course Overview

| Phase | Units | Level | Focus |
|-------|-------|-------|-------|
| Foundations | 1-5 | A1 | Cyrillic, verbs, all 6 cases |
| Building Blocks | 6-12 | A2 | Tenses, aspect, complex sentences |
| Intermediate | 13-18 | B1 | Motion verbs, conditionals, numbers |
| Upper-Int | 19-25 | B2 | Participles, gerunds, style |

## File Structure

```
ru/
├── CURRICULUM.md           # Full 25-unit course outline
├── README.md               # This file
├── __init__.py             # Main vocab factory (aggregates all units)
├── unit_one/               # Unit 1: First Steps (15 lessons)
│   ├── lessons/
│   │   ├── 00_stress.yaml      # CRITICAL: Stress marks intro
│   │   ├── 01_cognates.yaml
│   │   └── ...
│   └── vocab/
│       ├── __init__.py         # Unit factory
│       ├── _meta.yaml          # Unit metadata + pronunciation rules
│       ├── _lessons.yaml       # Lesson mappings
│       ├── pronouns.yaml       # Personal, demonstrative, possessive
│       ├── nouns.yaml          # Cognates + essential nouns
│       ├── verbs.yaml          # Type 1, Type 2, irregular
│       ├── adjectives.yaml     # Descriptive adjectives
│       ├── adverbs.yaml        # Location, interrogative, manner
│       ├── numerals.yaml       # Numbers
│       ├── particles.yaml      # да, нет, не, вот
│       ├── conjunctions.yaml   # и, или, но
│       ├── interjections.yaml  # Greetings, social expressions
│       └── phrases.yaml        # Multi-word expressions
├── unit_two/               # Unit 2: Everyday Life
│   └── vocab/              # Same modular structure
├── unit_three/             # Unit 3: Food & Drink
│   └── vocab/              # Same modular structure
└── ...
```

## Schema

```yaml
unit:
  id: "unit1"
  title: "Foundations"
  description: "Essential vocabulary for survival Russian"
  total_words: 65
  prerequisites: []  # Unit IDs that must be completed first

# Vocabulary is organized by theme/function
pronouns:
  - id: "ya"                    # Unique identifier for references
    word: "я"                   # Russian word (clean, for matching/TTS)
    stressed: "я"               # Stressed form with ́ marks for display
    transliteration: "ya"       # Pronunciation guide
    translation: "I"            # English meaning
    pos: "pronoun"              # Part of speech
    gender: null                # m/f/n for nouns
    frequency: 1                # 1 = very common, 3 = less common
    difficulty: 1               # 1 = easy, 3 = hard
    audio: "ya.mp3"             # Audio file reference
    notes: "Most common word"   # Teaching notes
    register: "informal"        # formal/informal/neutral
    examples:
      - { ru: "Я тут.", en: "I am here." }
    conjugation:                # For verbs only
      ya: "хочу́"               # Conjugations also show stress
      ty: "хо́чешь"
      ...

# Lesson mappings define what vocab goes where
lessons:
  lesson_1_cognates:
    title: "Cognates & Cyrillic"
    focus: "Letters identical to Latin"
    primary_vocab:    # New words taught in this lesson
      - mama
      - kot
      - taksi
    secondary_vocab:  # Supporting words
      - da
      - nyet
    review_vocab:     # Words from previous lessons to reinforce
      - eto
      - tam
```

## Design Principles

### 1. Stress Marks First
Russian stress is unpredictable and changes meaning. Every word includes:
- `word`: Clean form (for matching, TTS, user input)
- `stressed`: Display form with ́ accent marks (понима́ть, рабо́тать)

**Why this matters:**
- за́мок (castle) vs замо́к (lock) - same letters, different meaning!
- Unstressed О sounds like А (молоко́ = "malakó")
- Incorrect stress sounds very foreign to native speakers

### 2. Frequency First
Words are ordered by how often they appear in real Russian. Pronouns and question words come before obscure nouns.

### 3. Progressive Cyrillic
Letters are introduced in order of familiarity:
- Phase 1: Identical to Latin (А, Е, К, М, О, Т)
- Phase 2: False friends (Р=R, С=S, Н=N, В=V)
- Phase 3: Unique Cyrillic (Д, Б, Г, Ш, Щ, Ч, Ц, Й, Ы, Ь, Ъ, Э, Ю, Я)

### 4. Survival Vocabulary
Every word should answer: "Would a tourist need this in the first week?"

### 5. Natural Grammar
Grammar patterns emerge from vocabulary. Learn "У меня есть кот" before explaining genitive case.

### 6. Thematic Clusters
Related words taught together:
- да/нет (yes/no)
- тут/там (here/there)
- он/она/оно (he/she/it)

## Usage

### In Lessons
Reference vocabulary by ID:

```yaml
# In lesson file
vocabulary:
  from_unit: "unit1"  # unit ID from vocab YAML
  words:
    - ya
    - ty
    - on
```

### Direct Factory Access

```python
from data.content.ru import get_all_vocab, get_vocab, get_vocab_by_pos

# Get all vocab across units
all_vocab = get_all_vocab()  # Returns list with _unit tag

# Get single vocab by ID (O(1) lookup)
item = get_vocab("ya")

# Filter by PoS
verbs = get_vocab_by_pos("verb")
```

### Via VocabularyLoader

```python
from ingest.vocabulary import VocabularyLoader

loader = VocabularyLoader("ru")
unit = loader.load_unit("unit1")
lesson = loader.get_lesson_vocab("unit1", "lesson_01_cognates")
```

### Review Mixing

```python
loader = VocabularyLoader("ru")
review = loader.get_review_vocab("unit1", "lesson_01_cognates", max_items=10)
```

## Adding New Units

1. Create `unit_name/` folder with `lessons/` and `vocab/` subfolders
2. Add lesson YAML files to `lessons/`
3. Add vocabulary YAML to `vocab/`
4. Run ingestion script

```bash
python3 -m scripts.ingest_lessons --language ru
```
