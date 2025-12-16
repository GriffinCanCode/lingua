"""Template-Based Exercise Generation Engine

Fills sentence templates with vocabulary based on PoS and grammar constraints.
Like Mad Libs, but for language learning!

Template syntax:
  {SLOT}           - Any word matching slot constraints
  {SLOT.case}      - Word inflected to case (nom, gen, dat, acc, inst, prep)
  {SLOT.translation} - English translation of the word
"""
import re
import random
from dataclasses import dataclass, field
from itertools import product

from core.logging import engine_logger
from languages import get_module

log = engine_logger()

# Slot pattern: {WORD} or {WORD.modifier}
SLOT_PATTERN = re.compile(r'\{(\w+)(?:\.(\w+))?\}')

# Case abbreviations
CASE_ABBREV = {
    'nom': 'nominative', 'gen': 'genitive', 'dat': 'dative',
    'acc': 'accusative', 'inst': 'instrumental', 'prep': 'prepositional',
}


@dataclass(slots=True)
class SlotConstraint:
    """Constraints for what vocabulary can fill a slot."""
    pos: list[str] = field(default_factory=list)
    gender: list[str] = field(default_factory=list)
    semantic: list[str] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)  # Specific vocab IDs
    exclude_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'SlotConstraint':
        """Parse constraint from YAML dict."""
        return cls(
            pos=_ensure_list(data.get('pos', [])),
            gender=_ensure_list(data.get('gender', [])),
            semantic=_ensure_list(data.get('semantic', [])),
            ids=_ensure_list(data.get('ids', [])),
            exclude_ids=_ensure_list(data.get('exclude_ids', [])),
        )


@dataclass(slots=True)
class Template:
    """A sentence template with slots to fill."""
    pattern: str              # Russian pattern: "Это {NOUN.nom}."
    translation: str          # English pattern: "This is {NOUN.translation}."
    slots: dict[str, SlotConstraint]
    weight: int = 1           # How often to use this template

    @classmethod
    def from_dict(cls, data: dict) -> 'Template':
        """Parse template from YAML dict."""
        slots = {
            name: SlotConstraint.from_dict(constraints)
            for name, constraints in data.get('slots', {}).items()
        }
        return cls(
            pattern=data.get('pattern', ''),
            translation=data.get('translation', ''),
            slots=slots,
            weight=data.get('weight', 1),
        )


@dataclass(slots=True)
class VocabItem:
    """Vocabulary item with metadata for template matching."""
    id: str
    word: str
    translation: str
    pos: str = ''
    gender: str | None = None
    semantic: list[str] = field(default_factory=list)
    audio: str | None = None
    transliteration: str = ''


@dataclass(slots=True)
class FilledSentence:
    """A template filled with vocabulary."""
    text: str                 # "Это кот."
    translation: str          # "This is a cat."
    words: list[dict]         # Word alignment for word_bank
    source_vocab: list[str]   # IDs of vocab used
    distractors: list[str]    # Auto-generated distractors
    complexity: int = 1


class TemplateFiller:
    """Fills sentence templates with vocabulary."""

    __slots__ = ('_vocab', '_by_pos', '_by_semantic', '_by_id', '_lang', '_morph')

    def __init__(self, vocabulary: list[VocabItem], language: str = 'ru'):
        self._vocab = vocabulary
        self._lang = get_module(language)
        self._morph = self._lang.get_morphology_engine()

        # Build indexes for fast lookup
        self._by_pos: dict[str, list[VocabItem]] = {}
        self._by_semantic: dict[str, list[VocabItem]] = {}
        self._by_id: dict[str, VocabItem] = {}

        for v in vocabulary:
            self._by_id[v.id] = v
            self._by_pos.setdefault(v.pos, []).append(v)
            for sem in v.semantic:
                self._by_semantic.setdefault(sem, []).append(v)

        log.debug("template_filler_init", vocab_count=len(vocabulary), pos_groups=list(self._by_pos.keys()))

    def fill_template(self, template: Template, max_variants: int = 10) -> list[FilledSentence]:
        """Fill a template with compatible vocabulary combinations."""
        # Find matching vocab for each slot
        slot_options: dict[str, list[VocabItem]] = {}

        for slot_name, constraint in template.slots.items():
            matches = self._match_constraint(constraint)
            if not matches:
                log.warning("no_vocab_for_slot", slot=slot_name, constraint=constraint)
                return []
            slot_options[slot_name] = matches

        # Generate combinations (cartesian product)
        slot_names = list(slot_options.keys())
        combinations = list(product(*[slot_options[name] for name in slot_names]))

        # Limit combinations
        if len(combinations) > max_variants:
            combinations = random.sample(combinations, max_variants)

        results = []
        for combo in combinations:
            slot_values = dict(zip(slot_names, combo))
            filled = self._fill_one(template, slot_values)
            if filled:
                results.append(filled)

        return results

    def _match_constraint(self, constraint: SlotConstraint) -> list[VocabItem]:
        """Find vocabulary matching a constraint."""
        # Start with specific IDs if provided
        if constraint.ids:
            candidates = [self._by_id[vid] for vid in constraint.ids if vid in self._by_id]
        else:
            candidates = list(self._vocab)

        # Filter by PoS
        if constraint.pos:
            candidates = [v for v in candidates if v.pos in constraint.pos]

        # Filter by gender
        if constraint.gender:
            candidates = [v for v in candidates if v.gender in constraint.gender]

        # Filter by semantic tags
        if constraint.semantic:
            candidates = [v for v in candidates if any(s in v.semantic for s in constraint.semantic)]

        # Exclude specific IDs
        if constraint.exclude_ids:
            candidates = [v for v in candidates if v.id not in constraint.exclude_ids]

        return candidates

    def _fill_one(self, template: Template, slot_values: dict[str, VocabItem]) -> FilledSentence | None:
        """Fill template with specific vocab values."""
        text = template.pattern
        translation = template.translation
        words: list[dict] = []
        source_vocab: list[str] = []

        # Parse and fill each slot
        for match in SLOT_PATTERN.finditer(template.pattern):
            slot_name = match.group(1)
            modifier = match.group(2)
            full_match = match.group(0)

            if slot_name not in slot_values:
                continue

            vocab = slot_values[slot_name]
            source_vocab.append(vocab.id)

            # Get the form based on modifier
            ru_form = self._apply_modifier(vocab, modifier, 'ru')
            text = text.replace(full_match, ru_form, 1)

        # Fill translation pattern
        for match in SLOT_PATTERN.finditer(template.translation):
            slot_name = match.group(1)
            modifier = match.group(2)
            full_match = match.group(0)

            if slot_name not in slot_values:
                continue

            vocab = slot_values[slot_name]
            en_form = self._apply_modifier(vocab, modifier, 'en')
            translation = translation.replace(full_match, en_form, 1)

        # Build word alignment for exercises
        words = self._build_word_alignment(text, translation, slot_values)

        # Generate distractors
        distractors = self._generate_distractors(slot_values)

        return FilledSentence(
            text=text,
            translation=translation,
            words=words,
            source_vocab=source_vocab,
            distractors=distractors,
            complexity=len(slot_values),
        )

    def _apply_modifier(self, vocab: VocabItem, modifier: str | None, lang: str) -> str:
        """Apply modifier (case, translation) to get the right form."""
        if lang == 'en':
            base_word = re.sub(r'\s*\(.*?\)', '', vocab.translation).strip()
            
            if modifier == 'a':
                vowels = 'aeiou'
                article = 'an' if base_word.lower()[0] in vowels else 'a'
                return f"{article} {base_word}"
                
            if modifier == 'the':
                return f"the {base_word}"
                
            if modifier == 'translation' or not modifier:
                return base_word
            
            # For English, we mostly just use translation
            return base_word

        # Russian forms
        if not modifier:
            return vocab.word

        if modifier == 'translation':
            return vocab.translation

        # Case modifiers
        case = CASE_ABBREV.get(modifier)
        if case and self._morph:
            form = self._morph.generate_form(vocab.word, case, 'singular')
            if form:
                return form

        return vocab.word

    def _build_word_alignment(
        self,
        text: str,
        translation: str,
        slot_values: dict[str, VocabItem]
    ) -> list[dict]:
        """Build word alignment for word_bank exercises."""
        # Split into words
        ru_words = text.replace('.', '').replace('?', '').replace('!', '').replace(',', '').split()
        en_words = translation.replace('.', '').replace('?', '').replace('!', '').replace(',', '').split()

        # Create basic alignment - handle different sentence lengths
        words = []
        max_len = max(len(ru_words), len(en_words))
        
        for i in range(max_len):
            ru_word = ru_words[i] if i < len(ru_words) else None
            en_word = en_words[i] if i < len(en_words) else None
            words.append({'ru': ru_word, 'en': en_word})

        return words

    def _generate_distractors(self, slot_values: dict[str, VocabItem], count: int = 4) -> list[str]:
        """Generate distractor words for exercises."""
        used_ids = {v.id for v in slot_values.values()}
        distractors = []

        for vocab in slot_values.values():
            # Find same PoS, different words
            same_pos = [v for v in self._by_pos.get(vocab.pos, []) if v.id not in used_ids]
            for v in same_pos[:2]:
                distractors.append(v.translation)

        # Add some random words
        unused = [v for v in self._vocab if v.id not in used_ids]
        for v in random.sample(unused, min(count, len(unused))):
            if v.translation not in distractors:
                distractors.append(v.translation)

        return distractors[:count]

    def generate_sentences(
        self,
        templates: list[Template],
        count: int = 15,
        shuffle: bool = True,
    ) -> list[FilledSentence]:
        """Generate sentences from multiple templates."""
        all_sentences: list[FilledSentence] = []

        # Weight templates
        weighted: list[Template] = []
        for t in templates:
            weighted.extend([t] * t.weight)

        # Generate from templates
        attempts = 0
        max_attempts = count * 3

        while len(all_sentences) < count and attempts < max_attempts:
            template = random.choice(weighted) if weighted else templates[0]
            filled = self.fill_template(template, max_variants=3)
            for sent in filled:
                if sent.text not in {s.text for s in all_sentences}:
                    all_sentences.append(sent)
                    if len(all_sentences) >= count:
                        break
            attempts += 1

        if shuffle:
            random.shuffle(all_sentences)

        log.debug("sentences_generated", count=len(all_sentences), requested=count)
        return all_sentences[:count]


def _ensure_list(value) -> list:
    """Ensure value is a list."""
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def load_templates(data: dict) -> list[Template]:
    """Load templates from lesson YAML data."""
    templates_data = data.get('templates', [])
    return [Template.from_dict(t) for t in templates_data]


def load_dialogues(data: dict) -> list[dict]:
    """Load dialogues from lesson YAML data.
    
    Dialogue YAML structure:
    dialogues:
      - id: "cafe_order"
        context: "At a café"
        lines:
          - { speaker: "A", ru: "Кофе, пожалуйста.", en: "Coffee, please." }
          - { speaker: "B", ru: "Один?", en: "One?" }
    """
    return data.get('dialogues', [])


def create_filler_from_vocab_dicts(vocab_dicts: list[dict], language: str = 'ru') -> TemplateFiller:
    """Create TemplateFiller from vocabulary dictionaries."""
    vocab_items = [
        VocabItem(
            id=v.get('id', v.get('word', '')),
            word=v.get('word', ''),
            translation=v.get('translation', ''),
            pos=v.get('pos', ''),
            gender=v.get('gender'),
            semantic=v.get('semantic', []),
            audio=v.get('audio'),
            transliteration=v.get('transliteration', ''),
        )
        for v in vocab_dicts
    ]
    return TemplateFiller(vocab_items, language)
