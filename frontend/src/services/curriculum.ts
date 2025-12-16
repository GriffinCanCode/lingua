/**
 * Curriculum Service
 * 
 * Handles all curriculum-related API calls including:
 * - Learning path navigation
 * - Lesson generation
 * - Progress tracking
 */
import { api, handleApiError } from '../lib/api';

// === Types ===

export type LevelType = 'intro' | 'easy' | 'medium' | 'hard' | 'review';

export interface CurriculumNode {
  id: string;
  title: string;
  level: number;  // 1-7 within unit
  level_type: LevelType;
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  total_reviews: number;
  estimated_duration_min: number;
}

export interface CurriculumUnit {
  id: string;
  title: string;
  description: string | null;
  icon: string | null;
  is_checkpoint: boolean;
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  is_crowned: boolean;
  completed_nodes: number;
  total_nodes: number;
  nodes: CurriculumNode[];
}

export interface CurriculumSection {
  id: string;
  title: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  units: CurriculumUnit[];
}

export interface CurrentNode {
  node_id: string | null;
  node_title: string | null;
  unit_title: string | null;
  section_title: string | null;
}

export interface LessonSentence {
  sentence_id: string;
  text: string;
  translation: string | null;
  complexity: number;
  patterns: string[];
  teaching_value: number;
}

export interface Lesson {
  node_id: string;
  node_title: string;
  node_type: string;
  target_patterns: string[];
  sentences: LessonSentence[];
  estimated_duration_min: number;
  new_patterns: string[];
  review_patterns: string[];
  extra_data?: {
    content?: {
      introduction?: string;
    };
    vocabulary?: Array<{
      word: string;
      translation: string;
      audio?: string;
    }>;
  };
}

export interface LessonProgress {
  status: string;
  level: number;
  total_reviews: number;
  accuracy: number;
}

// === Exercise Types ===
import type { Exercise } from '../types/exercises';

export interface VocabItem {
  word: string;
  translation: string;
  audio?: string;
  hints?: string[];
  gender?: string;
}

export interface LessonExercises {
  node_id: string;
  node_title: string;
  level: number;
  level_type: LevelType;
  exercises: Exercise[];
  total_exercises: number;
  vocabulary: VocabItem[];
  content?: {
    introduction?: string;
  };
}

// === API Functions ===

/**
 * Get the full learning path with user progress
 */
export async function getLearningPath(language = 'ru'): Promise<CurriculumSection[]> {
  try {
    const response = await api.get<CurriculumSection[]>('/curriculum/path', {
      params: { language },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get the current node the user should work on
 */
export async function getCurrentNode(language = 'ru'): Promise<CurrentNode> {
  try {
    const response = await api.get<CurrentNode>('/curriculum/current', {
      params: { language },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}


/**
 * Get Duolingo-style exercises for a lesson node. Exercise distribution is based on the node's level_type.
 */
export async function getLessonExercises(nodeId: string, numExercises = 15, language = 'ru'): Promise<LessonExercises> {
  try {
    const response = await api.get<LessonExercises>(`/curriculum/nodes/${nodeId}/exercises`, {
      params: { num_exercises: numExercises, language },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Submit lesson completion and update progress
 */
export async function completeLesson(
  nodeId: string,
  correct: number,
  total: number,
  language = 'ru'
): Promise<LessonProgress> {
  try {
    const response = await api.post<LessonProgress>(
      `/curriculum/nodes/${nodeId}/complete`,
      { correct, total },
      { params: { language } }
    );
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Initialize progress for a new user
 */
export async function initializeProgress(language = 'ru'): Promise<void> {
  try {
    await api.post('/curriculum/initialize', null, {
      params: { language },
    });
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get all sections (admin/preview mode)
 */
export async function getSections(language = 'ru'): Promise<CurriculumSection[]> {
  try {
    const response = await api.get<CurriculumSection[]>('/curriculum/sections', {
      params: { language },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

// === Utility Functions ===

/**
 * Calculate overall progress for a section
 */
export function calculateSectionProgress(section: CurriculumSection): number {
  let completedNodes = 0;
  let totalNodes = 0;

  for (const unit of section.units) {
    completedNodes += unit.completed_nodes;
    totalNodes += unit.total_nodes;
  }

  return totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0;
}

/**
 * Find the next available node to work on
 */
export function findNextNode(sections: CurriculumSection[]): CurriculumNode | null {
  for (const section of sections) {
    for (const unit of section.units) {
      for (const node of unit.nodes) {
        if (node.status === 'available' || node.status === 'in_progress') {
          return node;
        }
      }
    }
  }
  return null;
}

/**
 * Count total crowns earned
 */
export function countCrowns(sections: CurriculumSection[]): number {
  let crowns = 0;
  for (const section of sections) {
    for (const unit of section.units) {
      if (unit.is_crowned) {
        crowns += 1;
      }
    }
  }
  return crowns;
}

/**
 * Get node status color for UI
 */
export function getNodeStatusColor(status: CurriculumNode['status']): string {
  switch (status) {
    case 'locked': return 'gray';
    case 'available': return 'sky';
    case 'in_progress': return 'blue';
    case 'completed': return 'green';
    case 'needs_practice': return 'amber';
    default: return 'gray';
  }
}

/**
 * Get readable status label
 */
export function getNodeStatusLabel(status: CurriculumNode['status']): string {
  switch (status) {
    case 'locked': return 'Locked';
    case 'available': return 'Start';
    case 'in_progress': return 'Continue';
    case 'completed': return 'Practice';
    case 'needs_practice': return 'Review';
    default: return 'Unknown';
  }
}

