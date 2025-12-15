import api from '../lib/api';

export interface Prompt {
  id: string;
  prompt_type: string;
  prompt_text: string;
  difficulty: number;
  hints: string[];
}

export interface ErrorDetail {
  error_type: string;
  description: string;
  correction: string;
  explanation: string;
  severity: number;
}

export interface Feedback {
  is_correct: string;
  score: number;
  errors: ErrorDetail[];
  corrected_text: string;
  suggestions: string[];
}

export interface AttemptResponse {
  id: string;
  prompt_id: string;
  user_response: string;
  is_correct: string;
  score: number;
  feedback: Feedback;
}

export const productionService = {
  getPrompts: async (promptType?: string) => {
    const response = await api.get<Prompt[]>('/production/prompts', {
      params: { prompt_type: promptType },
    });
    return response.data;
  },

  submitAttempt: async (promptId: string, userResponse: string, timeTaken?: number) => {
    const response = await api.post<AttemptResponse>('/production/attempt', {
      prompt_id: promptId,
      user_response: userResponse,
      time_taken_seconds: timeTaken,
    });
    return response.data;
  },

  getHistory: async () => {
    const response = await api.get<any[]>('/production/history');
    return response.data;
  },
  
  getStats: async () => {
    const response = await api.get<any>('/production/stats');
    return response.data;
  }
};

