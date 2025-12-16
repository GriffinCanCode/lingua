/**
 * Languages Service
 * 
 * Handles language configuration API calls including grammar data.
 */
import { api, handleApiError } from '../lib/api';

// === Types ===

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

export interface GenderConfig {
  id: string;
  label: string;
  short: string;
}

export interface NumberConfig {
  id: string;
  label: string;
}

export interface GrammarConfig {
  cases: CaseConfig[];
  genders: GenderConfig[];
  numbers: NumberConfig[];
  hasDeclension: boolean;
  hasConjugation: boolean;
}

export interface LanguageInfo {
  code: string;
  name: string;
  nativeName: string;
}

// Cache for grammar config
let grammarCache: Map<string, GrammarConfig> = new Map();

// === API Functions ===

/**
 * Get list of available languages
 */
export async function getAvailableLanguages(): Promise<LanguageInfo[]> {
  try {
    const response = await api.get<LanguageInfo[]>('/languages/');
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get language info by code
 */
export async function getLanguageInfo(langCode: string): Promise<LanguageInfo> {
  try {
    const response = await api.get<LanguageInfo>(`/languages/${langCode}`);
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get grammar configuration for a language (cases, genders, numbers)
 */
export async function getGrammarConfig(langCode: string): Promise<GrammarConfig> {
  // Check cache first
  if (grammarCache.has(langCode)) {
    return grammarCache.get(langCode)!;
  }

  try {
    const response = await api.get<GrammarConfig>(`/languages/${langCode}/grammar`);
    grammarCache.set(langCode, response.data);
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Clear grammar config cache
 */
export function clearGrammarCache(): void {
  grammarCache.clear();
}

// === Helper Functions ===

/**
 * Get case config by ID from grammar config
 */
export function getCaseById(grammar: GrammarConfig, caseId: string): CaseConfig | undefined {
  return grammar.cases.find(c => c.id === caseId);
}

/**
 * Get case label map from grammar config
 */
export function getCaseLabels(grammar: GrammarConfig): Record<string, string> {
  return grammar.cases.reduce((acc, c) => ({ ...acc, [c.id]: c.label }), {} as Record<string, string>);
}

/**
 * Get case hints map from grammar config
 */
export function getCaseHints(grammar: GrammarConfig): Record<string, string> {
  return grammar.cases.reduce((acc, c) => ({ ...acc, [c.id]: c.hint }), {} as Record<string, string>);
}

/**
 * Get case colors map from grammar config
 */
export function getCaseColors(grammar: GrammarConfig): Record<string, CaseColor> {
  return grammar.cases.reduce((acc, c) => ({ ...acc, [c.id]: c.color }), {} as Record<string, CaseColor>);
}
