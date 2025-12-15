import api from '../lib/api';

export interface SyntacticPattern {
  id: string;
  pattern_type: string;
  description?: string;
  difficulty: number;
}

export interface Sentence {
  id: string;
  text: string;
  language: string;
  translation?: string;
  complexity_score: number;
}

export interface ReviewItem {
  sentence: Sentence;
  patterns: SyntacticPattern[];
  due: boolean;
}

export interface ReviewResult {
  pattern_id: string;
  quality: number; // 0-5
}

export interface MasteryStats {
  pattern_id: string;
  pattern_type: string;
  mastery_level: number;
  next_review?: string;
  total_reviews: number;
}

export const srsService = {
  getDueReviews: async (limit: number = 10) => {
    const response = await api.get<ReviewItem[]>('/srs/due', {
      params: { limit },
    });
    return response.data;
  },

  submitReview: async (results: ReviewResult[]) => {
    const response = await api.post('/srs/review', results);
    return response.data;
  },

  getMasteryStats: async () => {
    const response = await api.get<MasteryStats[]>('/srs/mastery');
    return response.data;
  },
};

