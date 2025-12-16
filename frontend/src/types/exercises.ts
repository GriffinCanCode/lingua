/**
 * Exercise Type Definitions for Duolingo-style Lessons
 * Includes morphological pattern recognition exercises
 */

export type ExerciseType =
  | 'word_bank'
  | 'typing'
  | 'matching'
  | 'multiple_choice'
  | 'listen_select'
  | 'fill_blank'
  | 'pattern_fill'
  | 'paradigm_complete'
  | 'pattern_apply'
  | 'dialogue_translate';

export type TargetLanguage = 'ru' | 'en';
export type Difficulty = 1 | 2 | 3;
export type GrammaticalCase = 'nominative' | 'genitive' | 'dative' | 'accusative' | 'instrumental' | 'prepositional';
export type GrammaticalNumber = 'singular' | 'plural';
export type Gender = 'masculine' | 'feminine' | 'neuter';

// Morphological pattern definitions
export interface PatternEnding {
  singular: string;
  plural: string;
}

export interface MorphPattern {
  id: string;
  name: string;
  description: string;
  type: 'noun_declension' | 'verb_conjugation' | 'adjective_declension';
  paradigm: Record<GrammaticalCase, PatternEnding>;
  examples: string[];
}

// Word with morphological breakdown
export interface MorphWord {
  word: string;
  translation: string;
  stem: string;
  ending: string;
  gender?: Gender;
  pattern?: string;
  case?: GrammaticalCase;
  number?: GrammaticalNumber;
}

// Base exercise interface
export interface BaseExercise {
  id: string;
  type: ExerciseType;
  prompt: string;
  difficulty: Difficulty;
  hint?: string;
}

// Word Bank: Tap words to build a sentence
export interface WordBankExercise extends BaseExercise {
  type: 'word_bank';
  targetText: string;
  targetLanguage: TargetLanguage;
  wordBank: string[];
  translation: string;
}

// Typing: Free-form text input
export interface TypingExercise extends BaseExercise {
  type: 'typing';
  targetText: string;
  targetLanguage: TargetLanguage;
  acceptableAnswers: string[];
  sourceText: string;
}

// Matching: Match L1-L2 pairs
export interface MatchingPair {
  id: string;
  left: string;
  right: string;
}

export interface MatchingExercise extends BaseExercise {
  type: 'matching';
  pairs: MatchingPair[];
}

// Multiple Choice: Select correct translation
export interface MultipleChoiceExercise extends BaseExercise {
  type: 'multiple_choice';
  question: string;
  correctAnswer: string;
  options: string[];
  audioUrl?: string;
}

// Listen and Select: Audio prompt with options
export interface ListenSelectExercise extends BaseExercise {
  type: 'listen_select';
  audioUrl: string;
  correctAnswer: string;
  options: string[];
  transcript: string;
}

// Fill in the Blank: Complete the sentence
export interface FillBlankExercise extends BaseExercise {
  type: 'fill_blank';
  sentenceBefore: string;
  sentenceAfter: string;
  correctAnswer: string;
  options: string[];
  fullSentence: string;
}

// Pattern Fill: Select correct ending for stem + case
export interface PatternFillExercise extends BaseExercise {
  type: 'pattern_fill';
  stem: string;
  targetCase: GrammaticalCase;
  targetNumber: GrammaticalNumber;
  correctEnding: string;
  options: string[];
  baseWord: string;
  translation: string;
  patternName: string;
  fullForm: string;
}

// Paradigm Complete: Fill missing cells in declension table
export interface ParadigmCell {
  case: GrammaticalCase;
  number: GrammaticalNumber;
  form: string;
  isBlank: boolean;
}

export interface ParadigmCompleteExercise extends BaseExercise {
  type: 'paradigm_complete';
  lemma: string;
  translation: string;
  gender: Gender;
  patternName: string;
  cells: ParadigmCell[];
  blankIndices: number[];
  options: string[];
}

// Pattern Apply: Apply learned pattern to new word
export interface PatternApplyExercise extends BaseExercise {
  type: 'pattern_apply';
  newWord: string;
  newWordTranslation: string;
  targetCase: GrammaticalCase;
  targetNumber: GrammaticalNumber;
  patternName: string;
  exampleWord: string;
  exampleForm: string;
  correctAnswer: string;
  options: string[];
}

// Dialogue Line: Single line in conversation
export interface DialogueLine {
  speaker: string;
  ru: string;
  en: string;
}

// Dialogue Translate: Translate lines within conversation context
export interface DialogueTranslateExercise extends BaseExercise {
  type: 'dialogue_translate';
  context: string;
  dialogueId: string;
  dialogueLines: DialogueLine[];
  currentLineIndex: number;
  targetLanguage: TargetLanguage;
  sourceText: string;
  targetText: string;
}

// Union type for all exercises
export type Exercise =
  | WordBankExercise
  | TypingExercise
  | MatchingExercise
  | MultipleChoiceExercise
  | ListenSelectExercise
  | FillBlankExercise
  | PatternFillExercise
  | ParadigmCompleteExercise
  | PatternApplyExercise
  | DialogueTranslateExercise;

// Exercise result tracking
export interface ExerciseResult {
  exerciseId: string;
  correct: boolean;
  userAnswer: string | string[];
  timeSpentMs: number;
  attempts: number;
}

// Lesson exercise session
export interface LessonExercises {
  nodeId: string;
  nodeTitle: string;
  exercises: Exercise[];
  totalExercises: number;
  estimatedMinutes: number;
}

// Answer validation result
export interface ValidationResult {
  correct: boolean;
  correctAnswer: string;
  feedback?: string;
  typoDetected?: boolean;
}

// Exercise submission callback types
export type OnAnswerSubmit = (answer: string | string[], exercise: Exercise) => ValidationResult;
export type OnExerciseComplete = (result: ExerciseResult) => void;

// Grammar configuration from API
export interface CaseColor {
  bg: string;
  text: string;
  border: string;
}

export interface CaseConfig {
  id: string;
  label: string;
  hint: string;
  color: CaseColor;
}

export interface GrammarConfig {
  cases: CaseConfig[];
  genders: { id: string; label: string; short: string }[];
  numbers: { id: string; label: string }[];
  hasDeclension: boolean;
  hasConjugation: boolean;
}

// Common props for exercise components
export interface ExerciseComponentProps<T extends Exercise = Exercise> {
  exercise: T;
  onSubmit: (answer: string | string[]) => void;
  onSkip?: () => void;
  disabled?: boolean;
  grammarConfig?: GrammarConfig;
}
