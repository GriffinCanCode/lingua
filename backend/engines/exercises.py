"""Exercise Generator Engine

Generates Duolingo-style exercises from lesson vocabulary and sentences.
Supports: word_bank, typing, matching, multiple_choice, fill_blank,
          pattern_fill, paradigm_complete, pattern_apply, word_intro
"""
import random
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Literal

from core.logging import engine_logger
from languages import get_module, LanguageModule

log = engine_logger()

ExerciseType = Literal[
    'word_bank', 'typing', 'matching', 'multiple_choice', 'fill_blank',
    'pattern_fill', 'paradigm_complete', 'pattern_apply', 'word_intro',
    'dialogue_translate', 'error_correction'
]
TargetLanguage = Literal['ru', 'en']
LevelType = Literal['intro', 'easy', 'medium', 'hard', 'review']
VocabState = Literal['unseen', 'introduced', 'defined', 'practiced', 'mastered']
GrammaticalCase = Literal['nominative', 'genitive', 'dative', 'accusative', 'instrumental', 'prepositional']

# Exercise types appropriate for each vocabulary state
EXERCISE_TYPES_BY_STATE: dict[VocabState, list[ExerciseType]] = {
    'unseen': ['word_intro'],
    'introduced': ['word_intro', 'multiple_choice'],
    'defined': ['word_bank', 'multiple_choice', 'matching'],
    'practiced': ['word_bank', 'typing', 'fill_blank', 'pattern_fill', 'error_correction'],
    'mastered': ['typing', 'pattern_apply', 'paradigm_complete', 'error_correction'],
}


@dataclass(slots=True)
class VocabItem:
    """Vocabulary item from lesson."""
    word: str
    translation: str
    audio: str | None = None
    hints: list[str] = field(default_factory=list)
    gender: str | None = None
    stem: str | None = None
    pattern: str | None = None


@dataclass(slots=True)
class SentenceItem:
    """Sentence from lesson."""
    text: str
    translation: str
    words: list[dict] | None = None
    distractors: list[str] = field(default_factory=list)
    complexity: int = 1


@dataclass(slots=True)
class DialogueLine:
    """Single line in a dialogue."""
    speaker: str
    ru: str
    en: str


@dataclass(slots=True)
class DialogueItem:
    """Dialogue conversation block."""
    id: str
    context: str
    lines: list[DialogueLine]


@dataclass(slots=True)
class Exercise:
    """Base exercise structure."""
    id: str
    type: ExerciseType
    prompt: str
    difficulty: int
    data: dict


class ExerciseGenerator:
    """Generates varied exercises from lesson content including pattern-based morphology."""

    __slots__ = ('_distractor_pool', '_lang_module', '_morph')

    def __init__(self, language: str = "ru"):
        self._distractor_pool: dict[str, list[str]] = {}
        self._lang_module: LanguageModule = get_module(language)
        self._morph = self._lang_module.get_morphology_engine()
        log.debug("exercise_generator_initialized", language=language)

    def generate_lesson_exercises(
        self,
        vocabulary: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem] | None = None,
        num_exercises: int = 15,
        level_type: LevelType = 'medium',
    ) -> list[Exercise]:
        """Generate a balanced mix of exercises based on level type."""
        review_vocab = review_vocab or []
        all_vocab = vocabulary + review_vocab
        exercises: list[Exercise] = []

        # Build distractor pools using language module
        self._distractor_pool = {
            'ru': self._lang_module.build_distractor_pool([v.word for v in all_vocab], 'ru'),
            'en': self._lang_module.build_distractor_pool([v.translation for v in all_vocab], 'en'),
        }

        distributions: dict[str, dict[str, int]] = {
            'intro': {'word_bank': 6, 'multiple_choice': 2, 'pattern_fill': 2},
            'easy': {'word_bank': 4, 'multiple_choice': 3, 'matching': 1, 'pattern_fill': 2},
            'medium': {'word_bank': 4, 'multiple_choice': 2, 'typing': 1, 'fill_blank': 1, 'pattern_fill': 2},
            'hard': {'typing': 4, 'word_bank': 2, 'fill_blank': 1, 'pattern_fill': 2, 'paradigm_complete': 1, 'error_correction': 2},
            'review': {'word_bank': 2, 'typing': 2, 'multiple_choice': 2, 'matching': 1, 'pattern_fill': 2, 'pattern_apply': 1, 'error_correction': 1},
        }

        dist = distributions.get(level_type, distributions['medium'])
        if not dist:
            return []

        total_ratio = sum(dist.values())
        difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3, 'review': 2}
        base_difficulty = difficulty_map.get(level_type, 2)

        for ex_type, ratio in dist.items():
            count = max(1, round(num_exercises * ratio / total_ratio))
            exercises.extend(self._generate_by_type(ex_type, count, vocabulary, sentences, review_vocab, base_difficulty))

        random.shuffle(exercises)
        log.debug("exercises_generated", count=len(exercises[:num_exercises]), level_type=level_type)
        return exercises[:num_exercises]

    def _generate_by_type(
        self,
        ex_type: str,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
        dialogues: list[DialogueItem] | None = None,
    ) -> list[Exercise]:
        """Generate exercises of a specific type."""
        generators = {
            'word_bank': self._gen_word_bank,
            'typing': self._gen_typing,
            'matching': self._gen_matching,
            'multiple_choice': self._gen_multiple_choice,
            'fill_blank': self._gen_fill_blank,
            'pattern_fill': self._gen_pattern_fill,
            'paradigm_complete': self._gen_paradigm_complete,
            'pattern_apply': self._gen_pattern_apply,
            'error_correction': self._gen_error_correction,
        }
        if ex_type == 'dialogue_translate' and dialogues:
            return self._gen_dialogue_translate(count, dialogues, difficulty)
        gen = generators.get(ex_type)
        return gen(count, vocab, sentences, review_vocab, difficulty) if gen else []

    def _gen_word_bank(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate Duolingo-style word bank exercises - alternates directions."""
        exercises = []
        usable = [s for s in sentences if s.text and s.translation]
        if not usable:
            return []

        for i in range(count):
            sent = usable[i % len(usable)]
            to_russian = (i % 2 == 1)

            if to_russian:
                source = sent.translation
                target_lang: TargetLanguage = 'ru'
                correct_words = [w.get('ru', '') for w in sent.words if w.get('ru')] if sent.words else []
                if not correct_words:
                    correct_words = sent.text.replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
                distractors = self._get_distractors(correct_words, 'ru', max(3, len(correct_words)))
            else:
                source = sent.text
                target_lang = 'en'
                correct_words = [w.get('en', '') for w in sent.words if w.get('en')] if sent.words else []
                if not correct_words:
                    correct_words = sent.translation.replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
                distractors = sent.distractors[:max(3, len(correct_words))] if sent.distractors else self._get_distractors(correct_words, 'en', max(3, len(correct_words)))

            correct_words = [w for w in correct_words if w and w.strip()]
            if not correct_words:
                continue

            word_bank = correct_words + distractors
            random.shuffle(word_bank)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='word_bank',
                prompt='Translate this sentence',
                difficulty=min(3, sent.complexity),
                data={'targetText': ' '.join(correct_words), 'targetLanguage': target_lang, 'wordBank': word_bank, 'translation': source},
            ))

        return exercises

    def _gen_typing(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate typing exercises."""
        exercises = []
        all_vocab = vocab + review_vocab
        items = [(v.word, v.translation) for v in all_vocab]
        items += [(s.text, s.translation) for s in sentences if len(s.text.split()) <= 5]

        for i in range(min(count, len(items))):
            target_ru, target_en = items[i % len(items)]
            to_russian = difficulty >= 2

            exercises.append(Exercise(
                id=str(uuid4()),
                type='typing',
                prompt='Type the translation',
                difficulty=2 if len(target_ru.split()) <= 3 else 3,
                data={
                    'targetText': target_ru if to_russian else target_en,
                    'targetLanguage': 'ru' if to_russian else 'en',
                    'acceptableAnswers': [target_ru if to_russian else target_en],
                    'sourceText': target_en if to_russian else target_ru,
                },
            ))

        return exercises

    def _gen_matching(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate matching exercises (5 pairs each)."""
        exercises = []
        all_vocab = vocab + review_vocab

        if len(all_vocab) < 5:
            return []

        for _ in range(count):
            selected = random.sample(all_vocab, min(5, len(all_vocab)))
            pairs = [{'id': str(uuid4()), 'left': v.word, 'right': v.translation} for v in selected]
            exercises.append(Exercise(id=str(uuid4()), type='matching', prompt='Match the pairs', difficulty=difficulty, data={'pairs': pairs}))

        return exercises

    def _gen_multiple_choice(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate multiple choice exercises."""
        exercises = []
        all_vocab = vocab + review_vocab

        for i in range(min(count, len(all_vocab))):
            item = all_vocab[i % len(all_vocab)]
            wrong = [v.translation for v in all_vocab if v.word != item.word][:3]
            if len(wrong) < 3:
                wrong.extend(self._get_distractors([item.translation], 'en', 3 - len(wrong)))

            options = [item.translation] + wrong[:3]
            random.shuffle(options)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='multiple_choice',
                prompt='Choose the correct answer',
                difficulty=difficulty,
                data={'question': f"What does '{item.word}' mean?", 'correctAnswer': item.translation, 'options': options, 'audioUrl': item.audio},
            ))

        return exercises

    def _gen_fill_blank(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate fill-in-the-blank exercises."""
        exercises = []
        usable = [s for s in sentences if len(s.text.split()) >= 3]

        for i in range(min(count, len(usable))):
            sent = usable[i % len(usable)]
            words = sent.text.split()
            blank_idx = random.randint(1, len(words) - 1) if len(words) > 2 else 0
            correct = words[blank_idx]

            distractors = self._get_distractors([correct], 'ru', 3)
            options = [correct] + distractors
            random.shuffle(options)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='fill_blank',
                prompt='Complete the sentence',
                difficulty=difficulty,
                data={'sentenceBefore': ' '.join(words[:blank_idx]), 'sentenceAfter': ' '.join(words[blank_idx + 1:]), 'correctAnswer': correct, 'options': options, 'fullSentence': sent.text},
            ))

        return exercises

    def _gen_pattern_fill(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate pattern fill exercises - select correct ending for stem + case."""
        exercises = []
        all_vocab = vocab + review_vocab
        declinable = [v for v in all_vocab if v.gender in ('m', 'f', 'n')]
        if not declinable:
            return []

        cases = self._lang_module.get_cases() if hasattr(self._lang_module, 'get_cases') else ['genitive', 'accusative']
        target_cases: list[GrammaticalCase] = ['genitive', 'accusative'] if difficulty <= 2 else cases[1:]

        for i in range(min(count, len(declinable) * len(target_cases))):
            item = declinable[i % len(declinable)]
            target_case = target_cases[i % len(target_cases)]

            form = self._morph.generate_form(item.word, target_case, "singular")
            if not form:
                continue

            stem_data = self._morph.extract_stem_ending(form)
            if not stem_data.ending:
                continue

            options = self._morph.get_ending_options(target_case, stem_data.ending, 4)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='pattern_fill',
                prompt='Select the correct ending',
                difficulty=difficulty,
                data={
                    'stem': stem_data.stem,
                    'targetCase': target_case,
                    'targetNumber': 'singular',
                    'correctEnding': stem_data.ending,
                    'options': options,
                    'baseWord': item.word,
                    'translation': item.translation,
                    'patternName': stem_data.pattern_id or 'unknown',
                    'fullForm': form,
                },
            ))

        return exercises

    def _gen_paradigm_complete(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate paradigm completion exercises - fill missing cells in declension table."""
        exercises = []
        all_vocab = vocab + review_vocab
        declinable = [v for v in all_vocab if v.gender in ('m', 'f', 'n')]
        if not declinable:
            return []

        for i in range(min(count, len(declinable))):
            item = declinable[i % len(declinable)]
            paradigm = self._morph.get_pattern_paradigm(item.word, item.translation)

            if len(paradigm.cells) < 6:
                continue

            num_blanks = 2 if difficulty <= 2 else 4
            singular_cells = [c for c in paradigm.cells if c['number'] == 'singular']

            if len(singular_cells) < num_blanks:
                continue

            blank_indices = random.sample(range(len(singular_cells)), min(num_blanks, len(singular_cells)))

            cells = []
            all_options = set()
            for idx, cell in enumerate(singular_cells):
                is_blank = idx in blank_indices
                cells.append({'case': cell['case'], 'number': cell['number'], 'form': cell['form'], 'isBlank': is_blank})
                if is_blank:
                    all_options.add(cell['form'])

            distractor_forms = [c['form'] for c in singular_cells if c['form'] not in all_options][:2]
            options = list(all_options) + distractor_forms
            random.shuffle(options)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='paradigm_complete',
                prompt='Complete the paradigm table',
                difficulty=difficulty,
                data={
                    'lemma': paradigm.lemma,
                    'translation': paradigm.translation,
                    'gender': paradigm.gender,
                    'patternName': paradigm.pattern_name,
                    'cells': cells,
                    'blankIndices': blank_indices,
                    'options': options,
                },
            ))

        return exercises

    def _gen_pattern_apply(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate pattern apply exercises - apply learned pattern to new word."""
        exercises = []
        all_vocab = vocab + review_vocab
        declinable = [v for v in all_vocab if v.gender in ('m', 'f', 'n')]
        if len(declinable) < 2:
            return []

        target_cases: list[GrammaticalCase] = ['genitive', 'dative', 'accusative']

        for i in range(min(count, len(declinable))):
            example_item = declinable[i % len(declinable)]
            same_gender = [v for v in declinable if v.gender == example_item.gender and v.word != example_item.word]

            if not same_gender:
                continue

            new_item = random.choice(same_gender)
            target_case = target_cases[i % len(target_cases)]

            example_form = self._morph.generate_form(example_item.word, target_case, "singular")
            if not example_form:
                continue

            correct_form = self._morph.generate_form(new_item.word, target_case, "singular")
            if not correct_form:
                continue

            other_cases = [c for c in target_cases if c != target_case]
            distractors = []
            for other_case in other_cases[:2]:
                other_form = self._morph.generate_form(new_item.word, other_case, "singular")
                if other_form and other_form != correct_form:
                    distractors.append(other_form)

            if new_item.word != correct_form:
                distractors.append(new_item.word)

            options = [correct_form] + distractors[:3]
            random.shuffle(options)

            stem_data = self._morph.extract_stem_ending(example_item.word)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='pattern_apply',
                prompt='Apply the pattern to a new word',
                difficulty=difficulty,
                data={
                    'newWord': new_item.word,
                    'newWordTranslation': new_item.translation,
                    'targetCase': target_case,
                    'targetNumber': 'singular',
                    'patternName': stem_data.pattern_id or 'unknown',
                    'exampleWord': example_item.word,
                    'exampleForm': example_form,
                    'correctAnswer': correct_form,
                    'options': options,
                },
            ))

        return exercises

    def _gen_dialogue_translate(
        self,
        count: int,
        dialogues: list[DialogueItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate dialogue translation exercises - translate lines in conversation context."""
        exercises = []
        if not dialogues:
            return []

        for dialogue in dialogues:
            for idx, line in enumerate(dialogue.lines):
                # Alternate translation direction
                to_russian = idx % 2 == 0
                exercises.append(Exercise(
                    id=str(uuid4()),
                    type='dialogue_translate',
                    prompt='Translate this line',
                    difficulty=difficulty,
                    data={
                        'context': dialogue.context,
                        'dialogueId': dialogue.id,
                        'dialogueLines': [{'speaker': ln.speaker, 'ru': ln.ru, 'en': ln.en} for ln in dialogue.lines],
                        'currentLineIndex': idx,
                        'targetLanguage': 'ru' if to_russian else 'en',
                        'sourceText': line.en if to_russian else line.ru,
                        'targetText': line.ru if to_russian else line.en,
                    },
                ))
                if len(exercises) >= count:
                    return exercises

        return exercises[:count]

    def _gen_error_correction(
        self,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate error correction exercises - spot and fix grammar mistakes."""
        exercises = []
        all_vocab = vocab + review_vocab

        # Common error patterns for Russian
        error_generators = [
            self._make_gender_error,
            self._make_possessive_error,
            self._make_negation_error,
        ]

        usable = [s for s in sentences if len(s.text.split()) >= 3]
        if not usable:
            return []

        for i in range(count):
            sent = usable[i % len(usable)]
            gen_func = error_generators[i % len(error_generators)]
            error_data = gen_func(sent.text, all_vocab)

            if not error_data:
                continue

            exercises.append(Exercise(
                id=str(uuid4()),
                type='error_correction',
                prompt='Find and fix the error',
                difficulty=difficulty,
                data={
                    'incorrectSentence': error_data['incorrect'],
                    'correctSentence': error_data['correct'],
                    'errorType': error_data['error_type'],
                    'explanation': error_data['explanation'],
                    'translation': sent.translation,
                },
            ))

        return exercises

    def _make_gender_error(self, sentence: str, vocab: list[VocabItem]) -> dict | None:
        """Create gender agreement error (мой/моя́/моё mismatch)."""
        possessives = {'мой': 'моя́', 'моя́': 'мой', 'моё': 'моя́', 'твой': 'твоя́', 'твоя́': 'твой', 'наш': 'на́ша', 'на́ша': 'наш'}
        for poss, wrong in possessives.items():
            if poss in sentence:
                return {
                    'incorrect': sentence.replace(poss, wrong, 1),
                    'correct': sentence,
                    'error_type': 'gender_agreement',
                    'explanation': f"Wrong possessive gender: should be {poss}, not {wrong}",
                }
        return None

    def _make_possessive_error(self, sentence: str, vocab: list[VocabItem]) -> dict | None:
        """Create possessive form error."""
        if 'моя́' in sentence:
            return {'incorrect': sentence.replace('моя́', 'моё', 1), 'correct': sentence, 'error_type': 'possessive_form', 'explanation': "моё is neuter, use моя́ for feminine nouns"}
        if 'мой' in sentence and 'моя́' not in sentence:
            return {'incorrect': sentence.replace('мой', 'моё', 1), 'correct': sentence, 'error_type': 'possessive_form', 'explanation': "моё is neuter, use мой for masculine nouns"}
        return None

    def _make_negation_error(self, sentence: str, vocab: list[VocabItem]) -> dict | None:
        """Create negation position error."""
        if ' не ' in sentence:
            # Move не to wrong position
            words = sentence.split()
            ne_idx = words.index('не') if 'не' in words else -1
            if ne_idx > 0 and ne_idx < len(words) - 1:
                wrong_words = words.copy()
                wrong_words[ne_idx], wrong_words[ne_idx - 1] = wrong_words[ne_idx - 1], wrong_words[ne_idx]
                return {'incorrect': ' '.join(wrong_words), 'correct': sentence, 'error_type': 'word_order', 'explanation': "не should come directly before the verb"}
        return None

    def _get_distractors(self, exclude: list[str], lang: TargetLanguage, count: int) -> list[str]:
        """Get distractor words not in exclude list."""
        pool = self._distractor_pool.get(lang, [])
        exclude_lower = {w.lower() for w in exclude}
        available = [w for w in pool if w.lower() not in exclude_lower]
        return random.sample(available, min(count, len(available))) if available else []


def select_exercise_type(vocab_states: list[VocabState]) -> ExerciseType:
    """Randomly select appropriate exercise type based on vocab states."""
    eligible: set[ExerciseType] = set()
    for state in vocab_states:
        eligible.update(EXERCISE_TYPES_BY_STATE.get(state, []))
    return random.choice(list(eligible)) if eligible else 'multiple_choice'


def get_eligible_types_for_state(state: VocabState) -> list[ExerciseType]:
    """Get exercise types eligible for a vocabulary state."""
    return EXERCISE_TYPES_BY_STATE.get(state, ['multiple_choice'])


@dataclass(slots=True)
class StateAwareVocab:
    """Vocabulary item with tracking state."""
    word: str
    translation: str
    state: VocabState
    vocab_id: str
    audio: str | None = None
    gender: str | None = None
    pos: str | None = None


def generate_exercises(
    vocabulary: list[dict],
    sentences: list[dict],
    review_vocabulary: list[dict] | None = None,
    num_exercises: int = 15,
    level_type: str = 'medium',
    language: str = 'ru',
    dialogues: list[dict] | None = None,
) -> list[dict]:
    """Generate exercises from raw dict data (API-friendly)."""
    gen = ExerciseGenerator(language=language)

    vocab = [VocabItem(
        word=v['word'],
        translation=v['translation'],
        audio=v.get('audio'),
        hints=v.get('hints', []),
        gender=v.get('gender'),
        stem=v.get('stem'),
        pattern=v.get('pattern'),
    ) for v in vocabulary]

    sents = [SentenceItem(
        text=s['text'],
        translation=s['translation'],
        words=s.get('words'),
        distractors=s.get('distractors', []),
        complexity=s.get('complexity', 1),
    ) for s in sentences]

    review = [VocabItem(word=v['word'], translation=v['translation'], gender=v.get('gender')) for v in (review_vocabulary or [])]
    exercises = gen.generate_lesson_exercises(vocab, sents, review, num_exercises, level_type)

    # Add dialogue exercises if provided
    if dialogues:
        dialogue_items = [
            DialogueItem(
                id=d.get('id', str(uuid4())),
                context=d.get('context', ''),
                lines=[DialogueLine(speaker=ln['speaker'], ru=ln['ru'], en=ln['en']) for ln in d.get('lines', [])],
            ) for d in dialogues
        ]
        dialogue_exercises = gen._gen_dialogue_translate(len(dialogue_items) * 3, dialogue_items, 2)
        exercises.extend(dialogue_exercises)
        random.shuffle(exercises)

    return [{'id': ex.id, 'type': ex.type, 'prompt': ex.prompt, 'difficulty': ex.difficulty, **ex.data} for ex in exercises]


def generate_state_aware_exercises(
    vocab_pool: dict[str, list[StateAwareVocab]],
    sentences: list[dict],
    num_exercises: int = 15,
    language: str = 'ru',
) -> list[dict]:
    """Generate exercises based on vocabulary learning states.
    
    Args:
        vocab_pool: Dict with keys 'new', 'practice', 'review' containing StateAwareVocab items
        sentences: Sentence data for word_bank/fill_blank exercises
        num_exercises: Target number of exercises
        language: Target language code
    
    Returns:
        List of exercise dicts with type selected based on vocab state
    """
    gen = ExerciseGenerator(language=language)
    exercises: list[Exercise] = []

    new_vocab = vocab_pool.get('new', [])
    practice_vocab = vocab_pool.get('practice', [])
    review_vocab = vocab_pool.get('review', [])

    # Convert to VocabItem for existing generators
    all_vocab = [
        VocabItem(word=v.word, translation=v.translation, audio=v.audio, gender=v.gender)
        for v in new_vocab + practice_vocab + review_vocab
    ]

    sents = [SentenceItem(
        text=s['text'],
        translation=s['translation'],
        words=s.get('words'),
        distractors=s.get('distractors', []),
        complexity=s.get('complexity', 1),
    ) for s in sentences]

    # Build distractor pool
    gen._distractor_pool = {
        'ru': gen._lang_module.build_distractor_pool([v.word for v in all_vocab], 'ru'),
        'en': gen._lang_module.build_distractor_pool([v.translation for v in all_vocab], 'en'),
    }

    # Generate word_intro for new words first
    for v in new_vocab[:5]:
        exercises.append(Exercise(
            id=str(uuid4()),
            type='word_intro',
            prompt='Learn this word',
            difficulty=1,
            data={
                'word': v.word,
                'translation': v.translation,
                'audio': v.audio,
                'vocabId': v.vocab_id,
            },
        ))

    # Determine distribution based on pool composition
    remaining = num_exercises - len(exercises)
    if remaining <= 0:
        random.shuffle(exercises)
        return [{'id': ex.id, 'type': ex.type, 'prompt': ex.prompt, 'difficulty': ex.difficulty, **ex.data} for ex in exercises[:num_exercises]]

    # Collect states for type selection
    states = [v.state for v in practice_vocab + review_vocab]
    if not states:
        states = ['introduced']

    # Generate varied exercises based on states
    type_counts: dict[ExerciseType, int] = {}
    for _ in range(remaining):
        ex_type = select_exercise_type(states)
        type_counts[ex_type] = type_counts.get(ex_type, 0) + 1

    # Generate exercises by type
    practice_items = [VocabItem(word=v.word, translation=v.translation, audio=v.audio, gender=v.gender) for v in practice_vocab]
    review_items = [VocabItem(word=v.word, translation=v.translation, audio=v.audio, gender=v.gender) for v in review_vocab]

    for ex_type, count in type_counts.items():
        if ex_type == 'word_intro':
            continue  # Already handled
        generated = gen._generate_by_type(ex_type, count, practice_items, sents, review_items, 2)
        exercises.extend(generated)

    random.shuffle(exercises)
    log.debug("state_aware_exercises_generated", count=len(exercises), types=list(type_counts.keys()))
    return [{'id': ex.id, 'type': ex.type, 'prompt': ex.prompt, 'difficulty': ex.difficulty, **ex.data} for ex in exercises[:num_exercises]]
