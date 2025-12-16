import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, MessageCircle, Bot, User, Sparkles, BookOpen, Languages, ArrowLeft, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';

import {
  startChatSession,
  sendChatMessage,
  getCorrections,
  translateText,
  endChatSession,
  type ChatMessage,
  type ChatMode,
} from '../../services/chat';

// Chat bubble component
const ChatBubble: React.FC<{
  message: ChatMessage;
  showTranslation?: boolean;
  onTranslate?: () => void;
}> = ({ message, showTranslation, onTranslate }) => {
  const isUser = message.role === 'user';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={clsx("flex gap-3 mb-4", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div className={clsx(
        "w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-md",
        isUser ? "bg-blue-500" : "bg-gradient-to-br from-purple-500 to-pink-500"
      )}>
        {isUser ? <User size={20} className="text-white" /> : <Bot size={20} className="text-white" />}
      </div>
      
      {/* Message bubble */}
      <div className={clsx(
        "max-w-[75%] rounded-2xl px-4 py-3 shadow-sm",
        isUser 
          ? "bg-blue-500 text-white rounded-br-none" 
          : "bg-white border border-gray-100 rounded-bl-none"
      )}>
        <p className={clsx("text-base", isUser ? "text-white" : "text-gray-800")}>
          {message.content}
        </p>
        
        {/* Corrections */}
        {message.corrections && message.corrections.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            {message.corrections.map((c, idx) => (
              <p key={idx} className="text-sm text-amber-600">
                <span className="line-through">{c.original}</span> → <span className="font-medium">{c.corrected}</span>
                {c.explanation && <span className="text-gray-500 ml-1">({c.explanation})</span>}
              </p>
            ))}
          </div>
        )}
        
        {/* Translation */}
        {showTranslation && message.translation && (
          <p className="mt-2 text-sm text-gray-400 italic">{message.translation}</p>
        )}
        
        {/* Translate button for AI messages */}
        {!isUser && onTranslate && !showTranslation && (
          <button
            onClick={onTranslate}
            className="mt-2 text-xs text-purple-500 hover:text-purple-700 flex items-center gap-1"
          >
            <Languages size={12} /> Translate
          </button>
        )}
      </div>
    </motion.div>
  );
};

// Mode selector
const ModeSelector: React.FC<{
  mode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
}> = ({ mode, onModeChange }) => (
  <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
    {(['guided', 'freeform'] as ChatMode[]).map((m) => (
      <button
        key={m}
        onClick={() => onModeChange(m)}
        className={clsx(
          "flex-1 py-2 px-4 rounded-lg font-medium text-sm transition-all",
          mode === m
            ? "bg-white shadow-sm text-gray-900"
            : "text-gray-500 hover:text-gray-700"
        )}
      >
        {m === 'guided' ? (
          <span className="flex items-center justify-center gap-2">
            <BookOpen size={16} /> Guided
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Sparkles size={16} /> Freeform
          </span>
        )}
      </button>
    ))}
  </div>
);

// Typing indicator
const TypingIndicator: React.FC = () => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="flex gap-3 mb-4"
  >
    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-md">
      <Bot size={20} className="text-white" />
    </div>
    <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
            className="w-2 h-2 bg-gray-400 rounded-full"
          />
        ))}
      </div>
    </div>
  </motion.div>
);

// Main SpeechPractice component
export const SpeechPractice: React.FC = () => {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>('guided');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [translations, setTranslations] = useState<Record<string, string>>({});
  
  // UI state
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Start session
  const handleStartSession = useCallback(async () => {
    setLoading(true);
    try {
      const { sessionId: newSessionId, greeting } = await startChatSession(mode);
      setSessionId(newSessionId);
      setMessages([{
        id: crypto.randomUUID(),
        role: 'assistant',
        content: greeting,
      }]);
      setSessionStarted(true);
    } catch (err) {
      console.error('Failed to start session:', err);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [mode]);

  // Send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || !sessionId || loading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      // Check for corrections first
      const corrections = await getCorrections(input.trim());
      if (!corrections.is_correct && corrections.corrections.length > 0) {
        userMessage.corrections = corrections.corrections;
        setMessages(prev => prev.map(m => m.id === userMessage.id ? { ...m, corrections: corrections.corrections } : m));
      }

      // Get AI response
      const response = await sendChatMessage(sessionId, input.trim());
      setMessages(prev => [...prev, response]);
    } catch (err) {
      console.error('Failed to send message:', err);
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Извините, произошла ошибка. (Sorry, an error occurred.)',
      }]);
    } finally {
      setIsTyping(false);
      inputRef.current?.focus();
    }
  }, [input, sessionId, loading]);

  // Handle translate
  const handleTranslate = useCallback(async (messageId: string, text: string) => {
    try {
      const translation = await translateText(text, 'en');
      setTranslations(prev => ({ ...prev, [messageId]: translation }));
    } catch (err) {
      console.error('Translation failed:', err);
    }
  }, []);

  // Handle key press
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // End session on unmount
  useEffect(() => {
    return () => {
      if (sessionId) {
        endChatSession(sessionId).catch(() => {});
      }
    };
  }, [sessionId]);

  // Pre-session screen
  if (!sessionStarted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-purple-50 to-white">
        <div className="max-w-lg mx-auto px-4 py-12">
          {/* Header */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-8"
          >
            <ArrowLeft size={20} /> Back
          </button>

          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full mx-auto mb-4 flex items-center justify-center shadow-lg">
              <MessageCircle size={40} className="text-white" />
            </div>
            <h1 className="text-3xl font-black text-gray-900 mb-2">Speech Practice</h1>
            <p className="text-gray-500">Practice Russian conversation with an AI tutor</p>
          </div>

          {/* Mode selector */}
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <h2 className="font-bold text-gray-800 mb-4">Choose your mode</h2>
            <ModeSelector mode={mode} onModeChange={setMode} />
            
            <div className="mt-4 p-4 bg-gray-50 rounded-xl">
              {mode === 'guided' ? (
                <div className="text-sm text-gray-600">
                  <p className="font-medium text-purple-600 mb-1">📚 Guided Practice</p>
                  <p>Practice with vocabulary from your lessons. The AI will use simple sentences and help you stay on topic.</p>
                </div>
              ) : (
                <div className="text-sm text-gray-600">
                  <p className="font-medium text-pink-600 mb-1">✨ Freeform Chat</p>
                  <p>Talk about anything! The AI will adjust to your level and gently correct mistakes.</p>
                </div>
              )}
            </div>
          </div>

          {/* Start button */}
          <button
            onClick={handleStartSession}
            disabled={loading}
            className={clsx(
              "w-full py-4 rounded-2xl font-bold text-lg transition-all",
              "bg-gradient-to-r from-purple-500 to-pink-500 text-white",
              "hover:from-purple-600 hover:to-pink-600 shadow-lg",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "flex items-center justify-center gap-2"
            )}
          >
            {loading ? (
              <>
                <Loader2 size={24} className="animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <MessageCircle size={24} />
                Start Conversation
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Chat interface
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="p-2 hover:bg-gray-100 rounded-lg text-gray-500"
        >
          <ArrowLeft size={20} />
        </button>
        
        <div className="flex items-center gap-3 flex-1">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
            <Bot size={20} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-gray-900">Маша</h1>
            <p className="text-xs text-gray-500">
              {mode === 'guided' ? 'Guided Practice' : 'Freeform Chat'}
            </p>
          </div>
        </div>

        <div className="text-xs text-gray-400">
          {messages.length - 1} messages
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <AnimatePresence mode="popLayout">
          {messages.map((msg) => (
            <ChatBubble
              key={msg.id}
              message={{
                ...msg,
                translation: translations[msg.id],
              }}
              showTranslation={!!translations[msg.id]}
              onTranslate={msg.role === 'assistant' ? () => handleTranslate(msg.id, msg.content) : undefined}
            />
          ))}
        </AnimatePresence>
        
        <AnimatePresence>
          {isTyping && <TypingIndicator />}
        </AnimatePresence>
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-2xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type in Russian..."
            disabled={loading || isTyping}
            className={clsx(
              "flex-1 px-4 py-3 rounded-xl border-2 text-base transition-all",
              "focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100",
              "disabled:bg-gray-100 disabled:cursor-not-allowed",
              "border-gray-200"
            )}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || isTyping}
            className={clsx(
              "p-3 rounded-xl transition-all",
              input.trim()
                ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 shadow-md"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            )}
          >
            <Send size={24} />
          </button>
        </div>
        
        {/* Helper text */}
        <p className="text-center text-xs text-gray-400 mt-2">
          Press Enter to send • Маша will gently correct your mistakes
        </p>
      </div>
    </div>
  );
};

export default SpeechPractice;
