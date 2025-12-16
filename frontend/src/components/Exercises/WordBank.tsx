import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2 } from 'lucide-react';
import clsx from 'clsx';
import { microcopy } from '../../lib/microcopy';
import { Mascot } from '../Celebrations';
import type { WordBankExercise, ExerciseComponentProps } from '../../types/exercises';

interface WordChip {
  id: string;
  word: string;
  selected: boolean;
}

export const WordBank: React.FC<ExerciseComponentProps<WordBankExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [selectedWords, setSelectedWords] = useState<WordChip[]>([]);
  const [availableWords, setAvailableWords] = useState<WordChip[]>(() =>
    exercise.wordBank.map((word, i) => ({ id: `${i}-${word}`, word, selected: false }))
  );
  const [shake, setShake] = useState(false);

  const prompt = useMemo(() => microcopy.exercisePrompt('word_bank'), []);

  const handleWordSelect = useCallback((chip: WordChip) => {
    if (disabled || chip.selected) return;
    setAvailableWords(prev => prev.map(w => w.id === chip.id ? { ...w, selected: true } : w));
    setSelectedWords(prev => [...prev, { ...chip, selected: true }]);
  }, [disabled]);

  const handleWordRemove = useCallback((chip: WordChip) => {
    if (disabled) return;
    setSelectedWords(prev => prev.filter(w => w.id !== chip.id));
    setAvailableWords(prev => prev.map(w => w.id === chip.id ? { ...w, selected: false } : w));
  }, [disabled]);

  const currentAnswer = useMemo(() => 
    selectedWords.map(w => w.word).join(' '),
    [selectedWords]
  );

  const handleSubmit = useCallback(() => {
    if (selectedWords.length === 0) return;
    const normalizedAnswer = currentAnswer.toLowerCase().trim();
    const normalizedTarget = exercise.targetText.toLowerCase().trim();
    if (normalizedAnswer !== normalizedTarget) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
    }
    onSubmit(currentAnswer);
  }, [currentAnswer, exercise.targetText, onSubmit, selectedWords.length]);

  const handleClear = useCallback(() => {
    setSelectedWords([]);
    setAvailableWords(prev => prev.map(w => ({ ...w, selected: false })));
  }, []);

  const directionLabel = exercise.targetLanguage === 'ru' 
    ? 'Translate to Russian' 
    : 'Translate to English';

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-xs mb-4">
          {directionLabel}
        </p>
        
        {/* Source sentence with mascot */}
        <div className="flex items-start gap-4">
          <div className="shrink-0">
            <Mascot mood="happy" size={64} />
          </div>
          <div className="flex-1 bg-white rounded-2xl border-2 border-gray-200 p-4 relative shadow-sm">
            <div className="absolute left-[-8px] top-6 w-4 h-4 bg-white border-l-2 border-b-2 border-gray-200 transform rotate-45" />
            <p className="text-xl font-medium text-gray-900">
              {exercise.translation}
            </p>
            {exercise.hint && (
              <p className="text-sm text-gray-400 mt-1">{exercise.hint}</p>
            )}
          </div>
          <button 
            className="p-3 bg-blue-100 hover:bg-blue-200 rounded-full text-blue-600 transition-colors shrink-0"
            onClick={() => {/* Audio */}}
          >
            <Volume2 size={20} />
          </button>
        </div>
      </div>

      {/* Prompt */}
      <p className="text-sm text-gray-400 font-medium mb-2 text-center">{prompt}</p>

      {/* Answer Area */}
      <motion.div
        animate={shake ? { x: [-10, 10, -10, 10, 0] } : {}}
        transition={{ duration: 0.4 }}
        className={clsx(
          "min-h-[80px] p-4 mb-4 rounded-xl border-2 transition-colors",
          selectedWords.length > 0 
            ? "border-green-400 bg-green-50" 
            : "border-gray-200 bg-gray-50 border-dashed"
        )}
      >
        <div className="flex flex-wrap gap-2 min-h-[44px]">
          <AnimatePresence mode="popLayout">
            {selectedWords.map((chip) => (
              <motion.button
                key={chip.id}
                layout
                initial={{ opacity: 0, scale: 0.8, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                onClick={() => handleWordRemove(chip)}
                disabled={disabled}
                className={clsx(
                  "px-4 py-2 rounded-xl font-medium text-base transition-all",
                  "bg-[#58cc02] text-white border-2 border-[#4db302] border-b-4",
                  "hover:bg-[#4db302] active:border-b-2 active:translate-y-[2px]",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {chip.word}
              </motion.button>
            ))}
          </AnimatePresence>
          {selectedWords.length === 0 && (
            <span className="text-gray-400 italic">Tap words below...</span>
          )}
        </div>
      </motion.div>

      {/* Word Bank */}
      <div className="flex-1">
        <div className="flex flex-wrap gap-2 justify-center">
          {availableWords.map((chip) => (
            <motion.button
              key={chip.id}
              whileHover={!chip.selected && !disabled ? { scale: 1.02 } : {}}
              whileTap={!chip.selected && !disabled ? { scale: 0.98 } : {}}
              onClick={() => handleWordSelect(chip)}
              disabled={disabled || chip.selected}
              className={clsx(
                "px-4 py-2 rounded-xl font-medium text-base transition-all",
                "border-2 border-b-4",
                chip.selected
                  ? "bg-gray-100 border-gray-100 text-transparent cursor-default"
                  : "bg-white border-gray-300 text-gray-800 hover:border-gray-400 shadow-sm active:border-b-2 active:translate-y-[2px]",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {chip.word}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="mt-6 flex gap-3">
        {selectedWords.length > 0 && (
          <button
            onClick={handleClear}
            disabled={disabled}
            className="px-5 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 transition-colors"
          >
            Clear
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={disabled || selectedWords.length === 0}
          className={clsx(
            "flex-1 py-4 rounded-xl font-bold text-lg transition-all border-b-4 active:border-b-2 active:translate-y-[2px]",
            selectedWords.length > 0
              ? "bg-[#58cc02] text-white hover:bg-[#4db302] border-[#4db302] shadow-lg shadow-green-200"
              : "bg-gray-200 text-gray-400 cursor-not-allowed border-gray-300"
          )}
        >
          Check
        </button>
      </div>
    </div>
  );
};

export default WordBank;
