"""Exercise Generator Engine

Generates Duolingo-style exercises from lesson vocabulary and sentences.
Supports: word_bank, typing, matching, multiple_choice, fill_blank
"""
import random
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Literal

ExerciseType = Literal['word_bank', 'typing', 'matching', 'multiple_choice', 'fill_blank']
TargetLanguage = Literal['ru', 'en']
LevelType = Literal['intro', 'easy', 'medium', 'hard', 'review']


@dataclass(slots=True)
class VocabItem:
    """Vocabulary item from lesson."""
    word: str
    translation: str
    audio: str | None = None
    hints: list[str] = field(default_factory=list)
    gender: str | None = None


@dataclass(slots=True)
class SentenceItem:
    """Sentence from lesson."""
    text: str
    translation: str
    words: list[dict] | None = None  # [{ru: "...", en: "..."}]
    distractors: list[str] = field(default_factory=list)
    complexity: int = 1


@dataclass(slots=True)
class Exercise:
    """Base exercise structure."""
    id: str
    type: ExerciseType
    prompt: str
    difficulty: int
    data: dict  # Type-specific data


class ExerciseGenerator:
    """Generates varied exercises from lesson content."""

    __slots__ = ('_distractor_pool',)

    # Common Russian distractor words by difficulty
    DISTRACTORS_RU = {
        1: ['и', 'в', 'на', 'с', 'это', 'он', 'она', 'они', 'мы', 'я', 'ты', 'да', 'нет'],
        2: ['где', 'кто', 'что', 'как', 'тут', 'там', 'очень', 'хорошо', 'плохо', 'большой', 'маленький'],
        3: ['потому', 'когда', 'почему', 'сейчас', 'всегда', 'никогда', 'может', 'должен'],
    }

    DISTRACTORS_EN = {
        1: ['the', 'a', 'is', 'are', 'it', 'this', 'that', 'yes', 'no', 'and', 'or'],
        2: ['where', 'who', 'what', 'how', 'here', 'there', 'very', 'good', 'bad'],
        3: ['because', 'when', 'why', 'now', 'always', 'never', 'can', 'must'],
    }

    def __init__(self):
        self._distractor_pool: dict[str, list[str]] = {}

    def generate_lesson_exercises(
        self,
        vocabulary: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem] | None = None,
        num_exercises: int = 15,
        level_type: LevelType = 'medium',
    ) -> list[Exercise]:
        """
        Generate a balanced mix of exercises based on level type.

        Distribution varies by level_type:
        - intro: No exercises (uses WordIntro component)
        - easy: Mostly MC + matching (recognition)
        - medium: Word bank + some typing (production)
        - hard: Typing heavy (full production)
        - review: Balanced mix of all types
        """
        review_vocab = review_vocab or []
        all_vocab = vocabulary + review_vocab
        exercises: list[Exercise] = []

        # Build distractor pools
        self._distractor_pool = {
            'ru': self._build_distractor_pool([v.word for v in all_vocab], 'ru'),
            'en': self._build_distractor_pool([v.translation for v in all_vocab], 'en'),
        }

        # Distribution by level type (Duolingo-style: use words in sentences immediately)
        distributions: dict[str, dict[str, int]] = {
            'intro': {'word_bank': 8, 'multiple_choice': 2},  # Heavy word_bank for immediate sentence use
            'easy': {'word_bank': 5, 'multiple_choice': 4, 'matching': 1},
            'medium': {'word_bank': 5, 'multiple_choice': 3, 'typing': 1, 'fill_blank': 1},
            'hard': {'typing': 5, 'word_bank': 3, 'fill_blank': 2},
            'review': {'word_bank': 3, 'typing': 3, 'multiple_choice': 2, 'matching': 1, 'fill_blank': 1},
        }

        dist = distributions.get(level_type, distributions['medium'])
        if not dist:
            return []

        total_ratio = sum(dist.values())
        difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3, 'review': 2}
        base_difficulty = difficulty_map.get(level_type, 2)

        for ex_type, ratio in dist.items():
            count = max(1, round(num_exercises * ratio / total_ratio))
            exercises.extend(self._generate_by_type(
                ex_type, count, vocabulary, sentences, review_vocab, base_difficulty
            ))

        random.shuffle(exercises)
        return exercises[:num_exercises]

    def _generate_by_type(
        self,
        ex_type: str,
        count: int,
        vocab: list[VocabItem],
        sentences: list[SentenceItem],
        review_vocab: list[VocabItem],
        difficulty: int,
    ) -> list[Exercise]:
        """Generate exercises of a specific type."""
        generators = {
            'word_bank': self._gen_word_bank,
            'typing': self._gen_typing,
            'matching': self._gen_matching,
            'multiple_choice': self._gen_multiple_choice,
            'fill_blank': self._gen_fill_blank,
        }
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
            
            # Strictly alternate: even=English target, odd=Russian target
            to_russian = (i % 2 == 1)

            if to_russian:
                # User sees English, builds Russian (tap Russian words)
                source = sent.translation
                target_lang: TargetLanguage = 'ru'
                
                # Get Russian words from mapping, fallback to splitting sentence
                correct_words = []
                if sent.words:
                    correct_words = [w.get('ru', '') for w in sent.words if w.get('ru')]
                if not correct_words:
                    correct_words = sent.text.replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
                
                distractors = self._get_distractors(correct_words, 'ru', max(3, len(correct_words)))
            else:
                # User sees Russian, builds English (tap English words)
                source = sent.text
                target_lang = 'en'
                
                # Get English words from mapping, fallback to splitting translation
                correct_words = []
                if sent.words:
                    correct_words = [w.get('en', '') for w in sent.words if w.get('en')]
                if not correct_words:
                    correct_words = sent.translation.replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
                
                # Prefer sentence-specific distractors for English
                if sent.distractors:
                    distractors = sent.distractors[:max(3, len(correct_words))]
                else:
                    distractors = self._get_distractors(correct_words, 'en', max(3, len(correct_words)))

            # Filter empty strings and build word bank
            correct_words = [w for w in correct_words if w and w.strip()]
            if not correct_words:
                continue  # Skip if no valid words
                
            word_bank = correct_words + distractors
            random.shuffle(word_bank)

            exercises.append(Exercise(
                id=str(uuid4()),
                type='word_bank',
                prompt='Translate this sentence',
                difficulty=min(3, sent.complexity),
                data={
                    'targetText': ' '.join(correct_words),
                    'targetLanguage': target_lang,
                    'wordBank': word_bank,
                    'translation': source,
                },
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

        # Use shorter sentences or vocab for typing
        items = [(v.word, v.translation) for v in all_vocab]
        items += [(s.text, s.translation) for s in sentences if len(s.text.split()) <= 5]

        for i in range(min(count, len(items))):
            target_ru, target_en = items[i % len(items)]
            # Higher difficulty = type in target language
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
                data={
                    'question': f"What does '{item.word}' mean?",
                    'correctAnswer': item.translation,
                    'options': options,
                    'audioUrl': item.audio,
                },
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
                data={
                    'sentenceBefore': ' '.join(words[:blank_idx]),
                    'sentenceAfter': ' '.join(words[blank_idx + 1:]),
                    'correctAnswer': correct,
                    'options': options,
                    'fullSentence': sent.text,
                },
            ))

        return exercises

    def _build_distractor_pool(self, exclude: list[str], lang: TargetLanguage) -> list[str]:
        """Build pool of distractor words excluding lesson vocabulary."""
        exclude_lower = {w.lower() for w in exclude}
        base = self.DISTRACTORS_RU if lang == 'ru' else self.DISTRACTORS_EN
        pool = []
        for words in base.values():
            pool.extend(w for w in words if w.lower() not in exclude_lower)
        return pool

    def _get_distractors(self, exclude: list[str], lang: TargetLanguage, count: int) -> list[str]:
        """Get distractor words not in exclude list."""
        pool = self._distractor_pool.get(lang, [])
        exclude_lower = {w.lower() for w in exclude}
        available = [w for w in pool if w.lower() not in exclude_lower]
        return random.sample(available, min(count, len(available))) if available else []


# Convenience function for API use
def generate_exercises(
    vocabulary: list[dict],
    sentences: list[dict],
    review_vocabulary: list[dict] | None = None,
    num_exercises: int = 15,
    level_type: str = 'medium',
) -> list[dict]:
    """Generate exercises from raw dict data (API-friendly)."""
    gen = ExerciseGenerator()

    vocab = [VocabItem(
        word=v['word'],
        translation=v['translation'],
        audio=v.get('audio'),
        hints=v.get('hints', []),
        gender=v.get('gender'),
    ) for v in vocabulary]

    sents = [SentenceItem(
        text=s['text'],
        translation=s['translation'],
        words=s.get('words'),
        distractors=s.get('distractors', []),
        complexity=s.get('complexity', 1),
    ) for s in sentences]

    review = [VocabItem(word=v['word'], translation=v['translation']) for v in (review_vocabulary or [])]
    exercises = gen.generate_lesson_exercises(vocab, sents, review, num_exercises, level_type)

    return [{'id': ex.id, 'type': ex.type, 'prompt': ex.prompt, 'difficulty': ex.difficulty, **ex.data} for ex in exercises]
