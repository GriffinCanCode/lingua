import api from '../lib/api';

export interface EtymologyNode {
  id: string;
  word: string;
  language: string;
  meaning?: string;
  is_reconstructed: string;
}

export interface EtymologyEdge {
  source: string;
  target: string;
  relation_type: string;
  confidence: number;
}

export interface WordFamily {
  nodes: EtymologyNode[];
  edges: EtymologyEdge[];
}

export const etymologyService = {
  searchNodes: async (word: string, language?: string) => {
    const response = await api.get<EtymologyNode[]>('/etymology/search', {
      params: { word, language },
    });
    return response.data;
  },

  getWordFamily: async (nodeId: string, depth: number = 2) => {
    const response = await api.get<WordFamily>(`/etymology/word-family/${nodeId}`, {
      params: { depth },
    });
    return response.data;
  },

  findCognates: async (word: string, language: string = 'ru') => {
    const response = await api.get<EtymologyNode[]>(`/etymology/cognates/${word}`, {
      params: { source_language: language },
    });
    return response.data;
  },
};

