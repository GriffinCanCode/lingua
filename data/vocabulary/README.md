# Vocabulary Sheets

Master vocabulary files that drive the entire curriculum. Each unit has one vocabulary sheet containing all words, organized by theme.

## File Structure

```
vocabulary/
├── unit1_foundations.yaml   # ~65 words: pronouns, questions, basics
├── unit2_basics.yaml        # ~55 words: numbers, colors, verbs, food
├── unit3_grammar.yaml       # Cases, adjective agreement
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
  from_unit: "unit1"
  words:
    - ya
    - ty
    - on
```

### In Exercise Generation
The exercise generator pulls from vocabulary sheets:

```python
from ingest.vocabulary import get_lesson_vocabulary

vocab, review = get_lesson_vocabulary("unit1", "lesson_1_cognates")
exercises = generate_exercises(vocabulary=vocab, review_vocabulary=review)
```

### Review Mixing
The loader automatically provides previous lesson vocabulary for spaced repetition:

```python
loader = VocabularyLoader()
review = loader.get_review_vocab("unit1", "lesson_3", max_items=10)
# Returns vocab from lessons 1 & 2
```

## Adding New Units

1. Create `unitN_theme.yaml`
2. Add unit metadata
3. Add vocabulary sections (pronouns, nouns, verbs, etc.)
4. Define lesson mappings
5. Run vocabulary validation script

```bash
python3 -m scripts.validate_vocabulary
```
