import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { FillBlankExercise, ExerciseComponentProps } from '../../types/exercises';

export const FillBlank: React.FC<ExerciseComponentProps<FillBlankExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

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
        ? "bg-primary-500 text-white border-primary-600"
        : "bg-white border-gray-200 text-gray-800 hover:border-primary-300";
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
      <div className="text-center mb-8">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-4">
          Complete the sentence
        </p>
      </div>

      {/* Sentence with blank */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <p className="text-2xl md:text-3xl font-medium text-gray-800 text-center leading-relaxed">
          {exercise.sentenceBefore}
          <span className={clsx(
            "inline-block mx-2 px-4 py-1 min-w-[100px] rounded-lg border-2 border-dashed",
            selected
              ? submitted
                ? selected === exercise.correctAnswer
                  ? "border-green-400 bg-green-100 text-green-700"
                  : "border-red-400 bg-red-100 text-red-700"
                : "border-primary-400 bg-primary-100 text-primary-700"
              : "border-gray-300 bg-gray-50 text-gray-400"
          )}>
            {selected || '___'}
          </span>
          {exercise.sentenceAfter}
        </p>

        {exercise.hint && (
          <p className="text-sm text-gray-400 mt-4">{exercise.hint}</p>
        )}

        {/* Options */}
        <div className="flex flex-wrap gap-3 mt-8 justify-center">
          {shuffledOptions.map((option) => (
            <motion.button
              key={option}
              whileHover={!submitted ? { scale: 1.05 } : {}}
              whileTap={!submitted ? { scale: 0.95 } : {}}
              onClick={() => handleSelect(option)}
              disabled={disabled || submitted}
              className={clsx(
                "px-5 py-2 rounded-xl font-medium text-lg transition-all",
                "border-2 border-b-4",
                getOptionStyle(option)
              )}
            >
              {option}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !selected || submitted}
        className={clsx(
          "mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all",
          selected && !submitted
            ? "bg-primary-500 text-white hover:bg-primary-600 shadow-lg shadow-primary-200"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        )}
      >
        Check
      </button>
    </div>
  );
};

export default FillBlank;
