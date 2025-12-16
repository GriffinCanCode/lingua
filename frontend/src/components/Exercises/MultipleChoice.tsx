import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { Volume2 } from 'lucide-react';
import { microcopy } from '../../lib/microcopy';
import type { MultipleChoiceExercise, ExerciseComponentProps } from '../../types/exercises';

export const MultipleChoice: React.FC<ExerciseComponentProps<MultipleChoiceExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  
  const prompt = useMemo(() => microcopy.exercisePrompt('multiple_choice'), []);

  const shuffledOptions = useMemo(() =>
    [...exercise.options].sort(() => Math.random() - 0.5),
    [exercise.options]
  );

  const handleSelect = useCallback((option: string) => {
    if (disabled || submitted) return;
    setSelected(option);
  }, [disabled, submitted]);

  const handleSubmit = useCallback(() => {
    if (!selected) return;
    setSubmitted(true);
    setTimeout(() => onSubmit(selected), 300);
  }, [selected, onSubmit]);

  const playAudio = useCallback(() => {
    if (exercise.audioUrl) {
      const audio = new Audio(exercise.audioUrl);
      audio.play().catch(() => {});
    }
  }, [exercise.audioUrl]);

  const getOptionStyle = (option: string) => {
    if (!submitted) {
      return selected === option
        ? "bg-primary-100 border-primary-400 text-primary-700"
        : "bg-white border-gray-200 text-gray-800 hover:border-primary-300 hover:bg-primary-50";
    }
    if (option === exercise.correctAnswer) {
      return "bg-green-100 border-green-400 text-green-700";
    }
    if (option === selected && option !== exercise.correctAnswer) {
      return "bg-red-100 border-red-400 text-red-700";
    }
    return "bg-gray-50 border-gray-200 text-gray-400";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-4">
          {prompt}
        </p>

        {exercise.audioUrl && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={playAudio}
            className="mb-4 p-4 bg-primary-100 text-primary-600 rounded-full mx-auto block"
          >
            <Volume2 size={32} />
          </motion.button>
        )}

        <p className="text-2xl md:text-3xl font-medium text-gray-800">
          {exercise.question}
        </p>
        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-2">{exercise.hint}</p>
        )}
      </div>

      {/* Options */}
      <div className="flex-1 flex flex-col gap-3 max-w-lg mx-auto w-full">
        {shuffledOptions.map((option, index) => (
          <motion.button
            key={option}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            onClick={() => handleSelect(option)}
            disabled={disabled || submitted}
            className={clsx(
              "py-4 px-6 rounded-xl font-medium text-lg text-left transition-all",
              "border-2 border-b-4 active:border-b-2 active:translate-y-[2px]",
              getOptionStyle(option),
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <span className="inline-flex items-center gap-3">
              <span className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors",
                selected === option ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-500"
              )}>
                {index + 1}
              </span>
              {option}
            </span>
          </motion.button>
        ))}
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !selected || submitted}
        className={clsx(
          "mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all border-b-4 active:border-b-2 active:translate-y-[2px]",
          selected && !submitted
            ? "bg-[#58cc02] text-white hover:bg-[#4db302] border-[#4db302] shadow-lg shadow-green-200"
            : "bg-gray-200 text-gray-400 cursor-not-allowed border-gray-300"
        )}
      >
        Check
      </button>
    </div>
  );
};

export default MultipleChoice;
