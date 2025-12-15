import api from '../lib/api';

export interface Morpheme {
  word_index: number;
  morpheme_index: number;
  surface_form: string;
  gloss: string;
  morpheme_type?: string;
  lemma?: string;
}

export interface WordGloss {
  word: string;
  morphemes: Morpheme[];
  full_gloss: string;
}

export interface InterlinearLine {
  original: string[];
  morphemes: string[];
  glosses: string[];
  translation?: string;
}

export interface GlossedText {
  id: string;
  title?: string;
  original_text: string;
  language: string;
  translation?: string;
  difficulty: number;
}

export interface FullGlossedText {
  text: GlossedText;
  lines: InterlinearLine[];
}

export const glossingService = {
  glossText: async (text: string, language: string = 'ru') => {
    const response = await api.post<WordGloss[]>('/glossing/gloss', null, {
      params: { text, language },
    });
    return response.data;
  },

  getInterlinear: async (text: string, language: string = 'ru') => {
    const response = await api.get<InterlinearLine>('/glossing/interlinear', {
      params: { text, language },
    });
    return response.data;
  },

  getText: async (textId: string) => {
    const response = await api.get<FullGlossedText>(`/glossing/texts/${textId}`);
    return response.data;
  },

  listTexts: async (language: string = 'ru') => {
    const response = await api.get<GlossedText[]>('/glossing/texts', {
      params: { language },
    });
    return response.data;
  },
};

