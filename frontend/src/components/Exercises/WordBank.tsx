import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
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

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-4">
          {exercise.targetLanguage === 'ru' ? 'Translate to Russian' : 'Translate to English'}
        </p>
        <p className="text-2xl md:text-3xl font-medium text-gray-800">
          {exercise.translation}
        </p>
        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-2">{exercise.hint}</p>
        )}
      </div>

      {/* Answer Area */}
      <motion.div
        animate={shake ? { x: [-10, 10, -10, 10, 0] } : {}}
        transition={{ duration: 0.4 }}
        className={clsx(
          "min-h-[80px] p-4 mb-6 rounded-xl border-2 border-dashed transition-colors",
          selectedWords.length > 0 ? "border-primary-300 bg-primary-50" : "border-gray-200 bg-gray-50"
        )}
      >
        <div className="flex flex-wrap gap-2 min-h-[40px]">
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
                  "px-4 py-2 rounded-xl font-medium text-lg transition-all",
                  "bg-white border-2 border-gray-200 shadow-sm",
                  "hover:border-red-300 hover:bg-red-50",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {chip.word}
              </motion.button>
            ))}
          </AnimatePresence>
          {selectedWords.length === 0 && (
            <span className="text-gray-400 italic">Tap words below to build your answer</span>
          )}
        </div>
      </motion.div>

      {/* Word Bank */}
      <div className="flex-1">
        <div className="flex flex-wrap gap-2 justify-center">
          {availableWords.map((chip) => (
            <motion.button
              key={chip.id}
              whileHover={!chip.selected && !disabled ? { scale: 1.05 } : {}}
              whileTap={!chip.selected && !disabled ? { scale: 0.95 } : {}}
              onClick={() => handleWordSelect(chip)}
              disabled={disabled || chip.selected}
              className={clsx(
                "px-4 py-2 rounded-xl font-medium text-lg transition-all",
                "border-2 border-b-4",
                chip.selected
                  ? "bg-gray-100 border-gray-200 text-gray-300 cursor-default"
                  : "bg-white border-gray-200 hover:border-primary-300 hover:bg-primary-50 shadow-sm",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {chip.word}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="mt-8 flex gap-3">
        {selectedWords.length > 0 && (
          <button
            onClick={handleClear}
            disabled={disabled}
            className="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 transition-colors"
          >
            Clear
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={disabled || selectedWords.length === 0}
          className={clsx(
            "flex-1 py-4 rounded-xl font-bold text-lg transition-all",
            selectedWords.length > 0
              ? "bg-primary-500 text-white hover:bg-primary-600 shadow-lg shadow-primary-200"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          )}
        >
          Check
        </button>
      </div>
    </div>
  );
};

export default WordBank;
