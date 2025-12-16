# Russian Content

All Russian language content organized by unit.

## File Structure

```
ru/
├── unit_one/
│   ├── lessons/
│   │   ├── foundations.yaml
│   │   ├── 01_cognates.yaml
│   │   └── ...
│   └── vocab/
│       └── foundations.yaml
├── unit_two/
│   ├── lessons/
│   └── vocab/
│       └── basics.yaml
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
    word: "я"                   # Russian word
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
      ya: "хочу"
      ty: "хочешь"
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

### 1. Frequency First
Words are ordered by how often they appear in real Russian. Pronouns and question words come before obscure nouns.

### 2. Progressive Cyrillic
Letters are introduced in order of familiarity:
- Phase 1: Identical to Latin (А, Е, К, М, О, Т)
- Phase 2: False friends (Р=R, С=S, Н=N, В=V)
- Phase 3: Unique Cyrillic (Д, Б, Г, Ш, Щ, Ч, Ц, Й, Ы, Ь, Ъ, Э, Ю, Я)

### 3. Survival Vocabulary
Every word should answer: "Would a tourist need this in the first week?"

### 4. Natural Grammar
Grammar patterns emerge from vocabulary. Learn "У меня есть кот" before explaining genitive case.

### 5. Thematic Clusters
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

### In Exercise Generation

```python
from ingest.vocabulary import VocabularyLoader

loader = VocabularyLoader("ru")
unit = loader.load_unit("unit1")
```

### Review Mixing

```python
loader = VocabularyLoader("ru")
review = loader.get_review_vocab("unit1", "01_cognates", max_items=10)
```

## Adding New Units

1. Create `unit_name/` folder with `lessons/` and `vocab/` subfolders
2. Add lesson YAML files to `lessons/`
3. Add vocabulary YAML to `vocab/`
4. Run ingestion script

```bash
python3 -m scripts.ingest_lessons --language ru
```
