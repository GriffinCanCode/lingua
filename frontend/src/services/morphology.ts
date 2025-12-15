import api from '../lib/api';

export interface Lemma {
  id: string;
  word: string;
  language: string;
  part_of_speech: string;
  gender?: string;
  definition?: string;
}

export interface Inflection {
  form: string;
  case?: string;
  number?: string;
  person?: string;
  tense?: string;
  gender?: string;
}

export interface Paradigm {
  lemma: Lemma;
  inflections: Inflection[];
}

export const morphologyService = {
  searchLemmas: async (word: string, language: string = 'ru') => {
    const response = await api.get<Lemma[]>('/morphology/lemmas', {
      params: { word, language },
    });
    return response.data;
  },

  getParadigm: async (lemma: string, language: string = 'ru') => {
    const response = await api.get<Paradigm>(`/morphology/paradigm/${lemma}`, {
      params: { language },
    });
    return response.data;
  },

  analyzeWord: async (word: string, language: string = 'ru') => {
    const response = await api.get(`/morphology/analyze/${word}`, {
      params: { language },
    });
    return response.data;
  },
};

