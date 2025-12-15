import api from '../lib/api';

export interface MinimalPair {
  word1: string;
  word2: string;
  ipa1: string;
  ipa2: string;
  contrast: string;
  description: string;
}

export interface AcousticFeatures {
  duration_ms: number;
  f0_mean?: number;
  f0_range?: [number, number];
  formants?: Record<string, number>;
}

export interface PronunciationFeedback {
  target_word: string;
  target_ipa: string;
  user_ipa: string;
  accuracy_score: number;
  suggestions: string[];
}

export const phoneticsService = {
  getMinimalPairs: async (contrast?: string) => {
    const response = await api.get<MinimalPair[]>('/phonetics/minimal-pairs', {
      params: { contrast },
    });
    return response.data;
  },

  analyzeAudio: async (audioBlob: Blob, language: string = 'ru') => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    
    const response = await api.post<AcousticFeatures>('/phonetics/analyze-audio', formData, {
      params: { language },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  comparePronunciation: async (targetWord: string, audioBlob: Blob, language: string = 'ru') => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    
    const response = await api.post<PronunciationFeedback>('/phonetics/compare-pronunciation', formData, {
      params: { target_word: targetWord, language },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

