/**
 * Chat Service
 * 
 * Handles AI-powered conversation practice API calls including:
 * - Session management
 * - Message sending/receiving
 * - Grammar corrections
 * - Translation
 */
import { api, handleApiError } from '../lib/api';

// === Types ===

export type ChatMode = 'guided' | 'freeform';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  corrections?: Correction[];
  translation?: string;
}

export interface Correction {
  original: string;
  corrected: string;
  explanation: string;
}

export interface ChatSession {
  sessionId: string;
  mode: ChatMode;
  messages: ChatMessage[];
}

export interface StartSessionRequest {
  mode?: ChatMode;
  lesson_context?: string;
  vocabulary?: string[];
}

export interface StartSessionResponse {
  session_id: string;
  mode: string;
  greeting: string;
}

export interface SendMessageResponse {
  id: string;
  role: string;
  content: string;
  corrections?: Correction[];
  translation?: string;
}

export interface CorrectionsResponse {
  corrections: Correction[];
  is_correct: boolean;
}

export interface TranslateResponse {
  translation: string;
}

// === API Functions ===

/**
 * Start a new chat session
 */
export async function startChatSession(
  mode: ChatMode = 'guided',
  lessonContext?: string,
  vocabulary?: string[]
): Promise<{ sessionId: string; greeting: string; mode: ChatMode }> {
  try {
    const response = await api.post<StartSessionResponse>('/chat/start', {
      mode,
      lesson_context: lessonContext,
      vocabulary,
    });
    return {
      sessionId: response.data.session_id,
      greeting: response.data.greeting,
      mode: response.data.mode as ChatMode,
    };
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Send a message in an existing chat session
 */
export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ChatMessage> {
  try {
    const response = await api.post<SendMessageResponse>(
      `/chat/${sessionId}/message`,
      { message }
    );
    return {
      id: response.data.id,
      role: response.data.role as 'user' | 'assistant',
      content: response.data.content,
      corrections: response.data.corrections,
      translation: response.data.translation,
    };
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  try {
    const response = await api.get<{ messages: SendMessageResponse[] }>(
      `/chat/${sessionId}/history`
    );
    return response.data.messages.map(m => ({
      id: m.id,
      role: m.role as 'user' | 'assistant',
      content: m.content,
      corrections: m.corrections,
      translation: m.translation,
    }));
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Get grammar corrections for a Russian sentence
 */
export async function getCorrections(sentence: string): Promise<CorrectionsResponse> {
  try {
    const response = await api.post<CorrectionsResponse>('/chat/feedback', {
      sentence,
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * Translate text between Russian and English
 */
export async function translateText(
  text: string,
  toLang: 'ru' | 'en' = 'en'
): Promise<string> {
  try {
    const response = await api.post<TranslateResponse>('/chat/translate', {
      text,
      to_lang: toLang,
    });
    return response.data.translation;
  } catch (error) {
    throw handleApiError(error);
  }
}

/**
 * End a chat session
 */
export async function endChatSession(sessionId: string): Promise<void> {
  try {
    await api.delete(`/chat/${sessionId}`);
  } catch (error) {
    throw handleApiError(error);
  }
}
