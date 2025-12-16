/**
 * Teaching Content Type Definitions
 * Supports module-based lessons with etymology, patterns, and teaching cards
 */

// Module types within a lesson
export type ModuleType = 'intro' | 'learn' | 'pattern' | 'practice' | 'master';

// Teaching content types
export type TeachingContentType =
  | 'explanation'
  | 'pattern_table'
  | 'etymology'
  | 'morphology_pattern'
  | 'tip'
  | 'word_intro'
  | 'summary';

// Pattern table for grammar explanations
export interface PatternTableContent {
  type: 'pattern_table';
  title: string;
  columns: string[];
  rows: string[][];
  highlight?: number[]; // Row indices to highlight
}

// Etymology connection showing word relationships
export interface EtymologyConnection {
  word: string;
  lang: string;
  relation: 'cognate' | 'ancestor' | 'cousin' | 'descendant' | 'borrowing';
}

export interface EtymologyContent {
  type: 'etymology';
  title: string;
  word: string;
  connections: EtymologyConnection[];
  insight?: string;
}

// Morphological pattern with formula and examples
export interface PatternExample {
  ru: string;
  en: string;
}

export interface MorphologyPatternContent {
  type: 'morphology_pattern';
  title: string;
  formula: string;
  examples: PatternExample[];
  rule?: string;
}

// Simple explanation with markdown
export interface ExplanationContent {
  type: 'explanation';
  title: string;
  content: string;
}

// Tip callout box
export interface TipContent {
  type: 'tip';
  content: string;
}

// Word introduction cards
export interface WordIntroItem {
  word: string;
  translation: string;
  note?: string;
  audio?: string;
}

export interface WordIntroContent {
  type: 'word_intro';
  words: WordIntroItem[];
}

// Lesson summary
export interface SummaryContent {
  type: 'summary';
  title: string;
  points: string[];
}

// Union of all teaching content types
export type TeachingContent =
  | PatternTableContent
  | EtymologyContent
  | MorphologyPatternContent
  | ExplanationContent
  | TipContent
  | WordIntroContent
  | SummaryContent;

// Exercise config within a module
export interface ModuleExerciseConfig {
  count: number;
  templates?: { pattern: string; weight: number }[];
  review_previous?: boolean;
  difficulty?: 'easy' | 'medium' | 'hard';
}

// Module within a lesson
export interface Module {
  id: string;
  title: string;
  type: ModuleType;
  teaching: TeachingContent[];
  vocab_ids?: string[];
  exercises: ModuleExerciseConfig;
}

// Full lesson with modules
export interface ModularLesson {
  id: string;
  title: string;
  subtitle?: string;
  icon?: string;
  modules: Module[];
}

// Module progress tracking
export interface ModuleProgress {
  moduleId: string;
  completed: boolean;
  teachingViewed: boolean;
  exercisesCompleted: number;
  exercisesTotal: number;
  accuracy: number;
}

// Lesson session state for module flow
export interface LessonSessionState {
  lessonId: string;
  currentModuleIndex: number;
  phase: 'teaching' | 'exercises' | 'complete';
  teachingCardIndex: number;
  moduleProgress: ModuleProgress[];
}

// API response types
export interface ModuleExercisesResponse {
  moduleId: string;
  moduleTitle: string;
  moduleType: ModuleType;
  teaching: TeachingContent[];
  exercises: import('./exercises').Exercise[];
  totalExercises: number;
  vocabulary: import('../services/curriculum').VocabItem[];
}

export interface LessonModulesResponse {
  lessonId: string;
  lessonTitle: string;
  subtitle?: string;
  icon?: string;
  modules: {
    id: string;
    title: string;
    type: ModuleType;
    exerciseCount: number;
  }[];
  totalModules: number;
}
