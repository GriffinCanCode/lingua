import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, User } from 'lucide-react';
import clsx from 'clsx';
import type { DialogueTranslateExercise, ExerciseComponentProps, DialogueLine } from '../../types/exercises';

const SpeakerAvatar: React.FC<{ speaker: string; isUser?: boolean }> = ({ speaker, isUser }) => (
  <div className={clsx(
    "w-10 h-10 rounded-full flex items-center justify-center font-bold text-white shrink-0",
    isUser ? "bg-blue-500" : "bg-purple-500"
  )}>
    {speaker === 'A' ? <User size={20} /> : <MessageCircle size={20} />}
  </div>
);

const ChatBubble: React.FC<{
  line: DialogueLine;
  isCurrentLine: boolean;
  isPastLine: boolean;
  showTranslation: boolean;
  targetLanguage: 'ru' | 'en';
}> = ({ line, isCurrentLine, isPastLine, showTranslation, targetLanguage }) => {
  const isUserSide = line.speaker === 'A';
  const displayText = targetLanguage === 'ru' ? line.ru : line.en;
  const hintText = targetLanguage === 'ru' ? line.en : line.ru;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx("flex gap-3 mb-3", isUserSide ? "flex-row" : "flex-row-reverse")}
    >
      <SpeakerAvatar speaker={line.speaker} isUser={isUserSide} />
      <div className={clsx(
        "max-w-[70%] rounded-2xl px-4 py-2 relative",
        isUserSide ? "rounded-tl-none" : "rounded-tr-none",
        isCurrentLine 
          ? "bg-yellow-100 border-2 border-yellow-400 shadow-lg" 
          : isPastLine 
            ? "bg-gray-100 text-gray-600" 
            : "bg-gray-50 text-gray-400"
      )}>
        <p className={clsx("text-base", isCurrentLine && "font-medium")}>
          {isCurrentLine && !showTranslation ? (
            <span className="text-yellow-600 italic">??? (Your turn to translate)</span>
          ) : displayText}
        </p>
        {showTranslation && isPastLine && (
          <p className="text-xs text-gray-400 mt-1">{hintText}</p>
        )}
      </div>
    </motion.div>
  );
};

export const DialogueTranslate: React.FC<ExerciseComponentProps<DialogueTranslateExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [userInput, setUserInput] = useState('');
  const [shake, setShake] = useState(false);

  const { context, dialogueLines, currentLineIndex, targetLanguage, sourceText } = exercise;

  const directionLabel = targetLanguage === 'ru' 
    ? 'Translate to Russian' 
    : 'Translate to English';

  const handleSubmit = useCallback(() => {
    if (!userInput.trim()) return;
    const normalizedInput = userInput.toLowerCase().trim().replace(/[.,!?;:]/g, '');
    const normalizedTarget = exercise.targetText.toLowerCase().trim().replace(/[.,!?;:]/g, '');
    if (normalizedInput !== normalizedTarget) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }
    onSubmit(userInput.trim());
  }, [userInput, exercise.targetText, onSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const pastLines = useMemo(() => dialogueLines.slice(0, currentLineIndex), [dialogueLines, currentLineIndex]);
  const currentLine = useMemo(() => dialogueLines[currentLineIndex], [dialogueLines, currentLineIndex]);
  const futureLines = useMemo(() => dialogueLines.slice(currentLineIndex + 1), [dialogueLines, currentLineIndex]);

  return (
    <div className="flex flex-col h-full">
      {/* Context header */}
      <div className="mb-4 text-center">
        <span className="text-xs font-bold text-purple-600 uppercase tracking-wider bg-purple-100 px-3 py-1 rounded-full">
          {context}
        </span>
      </div>

      {/* Chat history */}
      <div className="flex-1 overflow-y-auto mb-4 px-2">
        {pastLines.map((line, idx) => (
          <ChatBubble
            key={`past-${idx}`}
            line={line}
            isCurrentLine={false}
            isPastLine={true}
            showTranslation={true}
            targetLanguage={targetLanguage}
          />
        ))}
        
        {currentLine && (
          <ChatBubble
            key="current"
            line={currentLine}
            isCurrentLine={true}
            isPastLine={false}
            showTranslation={false}
            targetLanguage={targetLanguage}
          />
        )}

        {futureLines.map((line, idx) => (
          <ChatBubble
            key={`future-${idx}`}
            line={line}
            isCurrentLine={false}
            isPastLine={false}
            showTranslation={false}
            targetLanguage={targetLanguage}
          />
        ))}
      </div>

      {/* Translation prompt */}
      <div className="bg-gray-50 rounded-xl p-4 mb-4">
        <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-2">
          {directionLabel}
        </p>
        <p className="text-lg font-medium text-gray-800">"{sourceText}"</p>
      </div>

      {/* Input area */}
      <motion.div
        animate={shake ? { x: [-10, 10, -10, 10, 0] } : {}}
        transition={{ duration: 0.4 }}
      >
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={`Type your translation in ${targetLanguage === 'ru' ? 'Russian' : 'English'}...`}
          autoFocus
          className={clsx(
            "w-full px-4 py-4 rounded-xl border-2 text-lg transition-all",
            "focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100",
            disabled ? "bg-gray-100 cursor-not-allowed" : "bg-white border-gray-200"
          )}
        />
      </motion.div>

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !userInput.trim()}
        className={clsx(
          "mt-4 w-full py-4 rounded-xl font-bold text-lg transition-all border-b-4 active:border-b-2 active:translate-y-[2px]",
          userInput.trim()
            ? "bg-[#58cc02] text-white hover:bg-[#4db302] border-[#4db302] shadow-lg shadow-green-200"
            : "bg-gray-200 text-gray-400 cursor-not-allowed border-gray-300"
        )}
      >
        Check
      </button>
    </div>
  );
};

export default DialogueTranslate;
