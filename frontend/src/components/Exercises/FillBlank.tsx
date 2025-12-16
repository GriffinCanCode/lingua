import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { microcopy } from '../../lib/microcopy';
import type { FillBlankExercise, ExerciseComponentProps } from '../../types/exercises';

export const FillBlank: React.FC<ExerciseComponentProps<FillBlankExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  
  const prompt = useMemo(() => microcopy.exercisePrompt('fill_blank'), []);

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

  const getOptionStyle = (option: string) => {
    if (!submitted) {
      return selected === option
        ? "bg-[#58cc02] text-white border-[#4db302]"
        : "bg-white border-gray-200 text-gray-800 hover:border-primary-300 hover:bg-primary-50";
    }
    if (option === exercise.correctAnswer) {
      return "bg-green-500 text-white border-green-600";
    }
    if (option === selected && option !== exercise.correctAnswer) {
      return "bg-red-500 text-white border-red-600";
    }
    return "bg-gray-100 border-gray-200 text-gray-400";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm">
          {prompt}
        </p>
      </div>

      {/* Sentence with blank */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <p className="text-2xl md:text-3xl font-medium text-gray-800 text-center leading-relaxed">
          {exercise.sentenceBefore}
          <motion.span 
            animate={selected ? { scale: [1, 1.05, 1] } : {}}
            className={clsx(
              "inline-block mx-2 px-4 py-1 min-w-[100px] rounded-lg border-2 border-dashed transition-all",
              selected
                ? submitted
                  ? selected === exercise.correctAnswer
                    ? "border-green-400 bg-green-100 text-green-700 border-solid"
                    : "border-red-400 bg-red-100 text-red-700 border-solid"
                  : "border-[#58cc02] bg-green-50 text-green-700 border-solid"
                : "border-gray-300 bg-gray-50 text-gray-400"
            )}
          >
            {selected || '___'}
          </motion.span>
          {exercise.sentenceAfter}
        </p>

        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-4">{exercise.hint}</p>
        )}

        {/* Options */}
        <div className="flex flex-wrap gap-3 mt-8 justify-center">
          {shuffledOptions.map((option, idx) => (
            <motion.button
              key={option}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              whileHover={!submitted ? { scale: 1.03 } : {}}
              whileTap={!submitted ? { scale: 0.97 } : {}}
              onClick={() => handleSelect(option)}
              disabled={disabled || submitted}
              className={clsx(
                "px-5 py-2 rounded-xl font-medium text-lg transition-all",
                "border-2 border-b-4 active:border-b-2 active:translate-y-[2px]",
                getOptionStyle(option)
              )}
            >
              {option}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Submit */}
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

export default FillBlank;
