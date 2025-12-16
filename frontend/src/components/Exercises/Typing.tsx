import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { microcopy } from '../../lib/microcopy';
import type { TypingExercise, ExerciseComponentProps } from '../../types/exercises';

const CYRILLIC_HINTS: Record<string, string> = {
  'а': 'f', 'б': ',', 'в': 'd', 'г': 'u', 'д': 'l', 'е': 't', 'ё': '`',
  'ж': ';', 'з': 'p', 'и': 'b', 'й': 'q', 'к': 'r', 'л': 'k', 'м': 'v',
  'н': 'y', 'о': 'j', 'п': 'g', 'р': 'h', 'с': 'c', 'т': 'n', 'у': 'e',
  'ф': 'a', 'х': '[', 'ц': 'w', 'ч': 'x', 'ш': 'i', 'щ': 'o', 'ъ': ']',
  'ы': 's', 'ь': 'm', 'э': "'", 'ю': '.', 'я': 'z',
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

  useEffect(() => { inputRef.current?.focus(); }, []);

  const prompt = React.useMemo(() => microcopy.exercisePrompt('typing'), []);

  const handleSubmit = useCallback(() => {
    if (!input.trim()) return;
    const normalize = (s: string) => s.toLowerCase().trim().replace(/\s+/g, ' ').replace(/[.,!?;:]/g, '');
    const normalizedInput = normalize(input);
    const normalizedTarget = normalize(exercise.targetText);

    const isMatch = normalizedInput === normalizedTarget || 
      exercise.acceptableAnswers.some(acc => normalize(acc) === normalizedInput);

    if (!isMatch) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }
    onSubmit(input.trim());
  }, [input, exercise.targetText, exercise.acceptableAnswers, onSubmit]);

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
          {exercise.targetLanguage === 'ru' ? 'Write in Russian' : 'Write in English'}
        </p>
        <p className="text-2xl md:text-3xl font-medium text-gray-800">
          {exercise.sourceText}
        </p>
        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-2">{exercise.hint}</p>
        )}
      </div>

      {/* Input */}
      <motion.div
        animate={shake ? { x: [-10, 10, -10, 10, 0] } : {}}
        transition={{ duration: 0.4 }}
        className="flex-1"
      >
        <p className="text-sm text-gray-400 font-medium mb-2">{prompt}</p>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={exercise.targetLanguage === 'ru' ? 'Введите ответ...' : 'Type your answer...'}
          className={clsx(
            "w-full h-32 p-4 text-xl text-gray-800 rounded-xl border-2 resize-none transition-all",
            "focus:outline-none focus:ring-2 focus:ring-primary-200",
            input ? "border-primary-400 bg-primary-50" : "border-gray-200 bg-white",
            disabled && "opacity-50 cursor-not-allowed bg-gray-100"
          )}
        />

        {/* Keyboard hints for Russian */}
        {exercise.targetLanguage === 'ru' && (
          <div className="mt-4">
            <button
              onClick={() => setShowKeyboardHint(!showKeyboardHint)}
              className="text-sm text-primary-500 hover:text-primary-600 font-medium"
            >
              {showKeyboardHint ? 'Hide' : 'Show'} keyboard layout
            </button>

            {showKeyboardHint && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-3 p-4 bg-gray-50 rounded-xl border border-gray-200"
              >
                <p className="text-xs text-gray-500 mb-3 font-medium">Russian ЙЦУКЕН layout:</p>
                <div className="grid grid-cols-11 gap-1 text-xs">
                  {Object.entries(CYRILLIC_HINTS).slice(0, 33).map(([cyr, lat]) => (
                    <div key={cyr} className="flex flex-col items-center p-1.5 bg-white rounded-lg border border-gray-200 shadow-sm">
                      <span className="font-bold text-gray-800">{cyr.toUpperCase()}</span>
                      <span className="text-gray-400 text-[10px]">{lat}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )}
      </motion.div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !input.trim()}
        className={clsx(
          "mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all border-b-4 active:border-b-2 active:translate-y-[2px]",
          input.trim()
            ? "bg-[#58cc02] text-white hover:bg-[#4db302] border-[#4db302] shadow-lg shadow-green-200"
            : "bg-gray-200 text-gray-400 cursor-not-allowed border-gray-300"
        )}
      >
        Check
      </button>
    </div>
  );
};

export default Typing;
