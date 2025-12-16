/**
 * Exercise Type Definitions for Duolingo-style Lessons
 */

export type ExerciseType =
  | 'word_bank'
  | 'typing'
  | 'matching'
  | 'multiple_choice'
  | 'listen_select'
  | 'fill_blank';

export type TargetLanguage = 'ru' | 'en';
export type Difficulty = 1 | 2 | 3;

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

// Union type for all exercises
export type Exercise =
  | WordBankExercise
  | TypingExercise
  | MatchingExercise
  | MultipleChoiceExercise
  | ListenSelectExercise
  | FillBlankExercise;

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

// Common props for exercise components
export interface ExerciseComponentProps<T extends Exercise = Exercise> {
  exercise: T;
  onSubmit: (answer: string | string[]) => void;
  onSkip?: () => void;
  disabled?: boolean;
}
