
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from engines.exercises import ExerciseGenerator, VocabItem, SentenceItem
from engines.templates import Template, TemplateFiller, VocabItem as TemplateVocabItem

def test_generation():
    # Mock vocabulary
    vocab = [
        {'id': 'kot', 'word': 'кот', 'translation': 'cat (male)', 'pos': 'noun', 'gender': 'm'},
        {'id': 'tam', 'word': 'там', 'translation': 'there', 'pos': 'adverb', 'semantic': ['location']}
    ]
    
    # Mock template
    template_data = {
        'pattern': '{NOUN} {LOCATION}.',
        'translation': '{NOUN.translation} is {LOCATION.translation}.',
        'slots': {
            'NOUN': {'ids': ['kot']},
            'LOCATION': {'ids': ['tam']}
        }
    }
    
    # Initialize TemplateFiller
    t_vocab = [TemplateVocabItem(**v) for v in vocab]
    filler = TemplateFiller(t_vocab)
    
    # Generate filled sentences
    template = Template.from_dict(template_data)
    filled_sentences = filler.generate_sentences([template], count=1)
    
    if not filled_sentences:
        print("No sentences generated")
        return

    sent = filled_sentences[0]
    print(f"Text: {sent.text}")
    print(f"Translation: {sent.translation}")
    print(f"Words: {sent.words}")
    
    # Now generate exercise
    gen = ExerciseGenerator()
    
    # Convert filled sentence to SentenceItem
    s_item = SentenceItem(
        text=sent.text,
        translation=sent.translation,
        words=sent.words,
        distractors=sent.distractors
    )
    
    exercises = gen.generate_lesson_exercises(
        vocabulary=[VocabItem(word=v['word'], translation=v['translation']) for v in vocab],
        sentences=[s_item],
        num_exercises=1,
        level_type='medium'
    )
    
    for ex in exercises:
        if ex.type == 'word_bank':
            print("\nExercise:")
            print(f"Prompt: {ex.prompt}")
            print(f"Target Text: {ex.data['targetText']}")
            print(f"Word Bank: {ex.data['wordBank']}")

if __name__ == '__main__':
    test_generation()
