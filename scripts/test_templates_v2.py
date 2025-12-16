
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
        {'id': 'apple', 'word': 'яблоко', 'translation': 'apple', 'pos': 'noun', 'gender': 'n'},
        {'id': 'tam', 'word': 'там', 'translation': 'there', 'pos': 'adverb', 'semantic': ['location']}
    ]
    
    # Mock templates
    templates_data = [
        {
            'pattern': 'Это {NOUN}.',
            'translation': 'This is {NOUN.a}.',
            'slots': {'NOUN': {'ids': ['kot', 'apple']}}
        },
        {
            'pattern': '{NOUN} {LOCATION}.',
            'translation': '{NOUN.the} is {LOCATION.translation}.',
            'slots': {'NOUN': {'ids': ['kot']}, 'LOCATION': {'ids': ['tam']}}
        }
    ]
    
    # Initialize TemplateFiller
    t_vocab = [TemplateVocabItem(**v) for v in vocab]
    filler = TemplateFiller(t_vocab)
    
    print("Testing templates...")
    for t_data in templates_data:
        template = Template.from_dict(t_data)
        filled_sentences = filler.generate_sentences([template], count=2)
        
        for sent in filled_sentences:
            print(f"Pattern: {t_data['pattern']}")
            print(f"Text: {sent.text}")
            print(f"Translation: {sent.translation}")
            print(f"Words: {sent.words}")
            print("-" * 20)

if __name__ == '__main__':
    test_generation()
