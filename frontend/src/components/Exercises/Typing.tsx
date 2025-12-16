import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { TypingExercise, ExerciseComponentProps } from '../../types/exercises';

// Cyrillic keyboard layout hints
const CYRILLIC_HINTS: Record<string, string> = {
  'а': 'f', 'б': ',', 'в': 'd', 'г': 'u', 'д': 'l', 'е': 't', 'ё': '`',
  'ж': ';', 'з': 'p', 'и': 'b', 'й': 'q', 'к': 'r', 'л': 'k', 'м': 'v',
  'н': 'y', 'о': 'j', 'п': 'g', 'р': 'h', 'с': 'c', 'т': 'n', 'у': 'e',
  'ф': 'a', 'х': '[', 'ц': 'w', 'ч': 'x', 'ш': 'i', 'щ': 'o', 'ъ': ']',
  'ы': 's', 'ь': 'm', 'э': "'", 'ю': '.', 'я': 'z',
};

// Levenshtein distance for typo detection
const levenshtein = (a: string, b: string): number => {
  const matrix: number[][] = [];
  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      matrix[i][j] = b[i - 1] === a[j - 1]
        ? matrix[i - 1][j - 1]
        : Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1);
    }
  }
  return matrix[b.length][a.length];
};

export const Typing: React.FC<ExerciseComponentProps<TypingExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const [shake, setShake] = useState(false);
  const [showKeyboardHint, setShowKeyboardHint] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const normalizeText = (text: string): string =>
    text.toLowerCase().trim().replace(/\s+/g, ' ').replace(/[.,!?;:]/g, '');

  const isCloseEnough = (userInput: string, target: string): boolean => {
    const normalizedInput = normalizeText(userInput);
    const normalizedTarget = normalizeText(target);

    if (normalizedInput === normalizedTarget) return true;

    // Check acceptable answers
    for (const acceptable of exercise.acceptableAnswers) {
      if (normalizeText(acceptable) === normalizedInput) return true;
    }

    // Allow minor typos (1 char for short, 2 for longer)
    const maxDistance = normalizedTarget.length > 10 ? 2 : 1;
    return levenshtein(normalizedInput, normalizedTarget) <= maxDistance;
  };

  const handleSubmit = useCallback(() => {
    if (!input.trim()) return;

    if (!isCloseEnough(input, exercise.targetText)) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }

    onSubmit(input.trim());
  }, [input, exercise.targetText, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-4">
          {exercise.targetLanguage === 'ru' ? 'Type in Russian' : 'Type in English'}
        </p>
        <p className="text-2xl md:text-3xl font-medium text-gray-800">
          {exercise.sourceText}
        </p>
        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-2">{exercise.hint}</p>
        )}
      </div>

      {/* Input Area */}
      <motion.div
        animate={shake ? { x: [-10, 10, -10, 10, 0] } : {}}
        transition={{ duration: 0.4 }}
        className="flex-1"
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={exercise.targetLanguage === 'ru' ? 'Введите ответ...' : 'Type your answer...'}
          className={clsx(
            "w-full h-32 p-4 text-xl rounded-xl border-2 resize-none transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-primary-200",
            input ? "border-primary-300 bg-primary-50" : "border-gray-200",
            disabled && "opacity-50 cursor-not-allowed bg-gray-100"
          )}
        />

        {/* Keyboard hint toggle for Russian */}
        {exercise.targetLanguage === 'ru' && (
          <div className="mt-4">
            <button
              onClick={() => setShowKeyboardHint(!showKeyboardHint)}
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              {showKeyboardHint ? 'Hide' : 'Show'} keyboard hints
            </button>

            {showKeyboardHint && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-3 p-4 bg-gray-50 rounded-xl"
              >
                <p className="text-xs text-gray-500 mb-2">Russian keyboard (phonetic layout):</p>
                <div className="grid grid-cols-11 gap-1 text-xs">
                  {Object.entries(CYRILLIC_HINTS).slice(0, 33).map(([cyr, lat]) => (
                    <div key={cyr} className="flex flex-col items-center p-1 bg-white rounded border">
                      <span className="font-bold text-gray-800">{cyr.toUpperCase()}</span>
                      <span className="text-gray-400">{lat}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )}
      </motion.div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !input.trim()}
        className={clsx(
          "mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all",
          input.trim()
            ? "bg-primary-500 text-white hover:bg-primary-600 shadow-lg shadow-primary-200"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        )}
      >
        Check
      </button>
    </div>
  );
};

export default Typing;
