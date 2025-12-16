import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Lightbulb } from 'lucide-react';
import clsx from 'clsx';
import type { PatternApplyExercise, ExerciseComponentProps, GrammaticalCase } from '../../types/exercises';

const CASE_LABELS: Record<GrammaticalCase, string> = {
  nominative: 'Nominative',
  genitive: 'Genitive',
  dative: 'Dative',
  accusative: 'Accusative',
  instrumental: 'Instrumental',
  prepositional: 'Prepositional',
};

const CASE_COLORS: Record<GrammaticalCase, { bg: string; text: string }> = {
  nominative: { bg: 'bg-blue-100', text: 'text-blue-700' },
  genitive: { bg: 'bg-green-100', text: 'text-green-700' },
  dative: { bg: 'bg-orange-100', text: 'text-orange-700' },
  accusative: { bg: 'bg-purple-100', text: 'text-purple-700' },
  instrumental: { bg: 'bg-pink-100', text: 'text-pink-700' },
  prepositional: { bg: 'bg-cyan-100', text: 'text-cyan-700' },
};

export const PatternApply: React.FC<ExerciseComponentProps<PatternApplyExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const shuffledOptions = useMemo(
    () => [...exercise.options].sort(() => Math.random() - 0.5),
    [exercise.options]
  );

  const caseColors = CASE_COLORS[exercise.targetCase];

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
        ? 'bg-primary-500 text-white border-primary-600'
        : 'bg-white border-gray-200 text-gray-800 hover:border-primary-300';
    }

    if (option === exercise.correctAnswer) {
      return 'bg-green-500 text-white border-green-600';
    }
    if (option === selected && option !== exercise.correctAnswer) {
      return 'bg-red-500 text-white border-red-600';
    }
    return 'bg-gray-100 border-gray-200 text-gray-400';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="text-center mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-2">
          Apply the pattern
        </p>
        <div className={clsx(
          'inline-block px-3 py-1 rounded-full text-xs font-bold',
          caseColors.bg, caseColors.text
        )}>
          {CASE_LABELS[exercise.targetCase]}
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center">
        {/* Example transformation */}
        <div className="bg-indigo-50 rounded-xl p-6 mb-8 w-full max-w-md">
          <div className="flex items-start gap-2 mb-3">
            <Lightbulb className="text-indigo-500 flex-shrink-0 mt-0.5" size={18} />
            <span className="text-sm font-medium text-indigo-700">Example</span>
          </div>
          <div className="flex items-center justify-center gap-4">
            <div className="text-center">
              <span className="text-lg font-bold text-gray-700">{exercise.exampleWord}</span>
              <span className="block text-xs text-gray-500 mt-1">nominative</span>
            </div>
            <ArrowRight className="text-indigo-400" size={24} />
            <div className="text-center">
              <span className={clsx('text-lg font-bold', caseColors.text)}>{exercise.exampleForm}</span>
              <span className="block text-xs text-gray-500 mt-1">{exercise.targetCase}</span>
            </div>
          </div>
        </div>

        {/* Question */}
        <div className="text-center mb-8">
          <p className="text-gray-500 text-sm mb-2">Now transform:</p>
          <div className="flex items-center justify-center gap-4">
            <div className="text-center">
              <span className="text-2xl font-bold text-gray-800">{exercise.newWord}</span>
              <span className="block text-sm text-gray-500 mt-1">{exercise.newWordTranslation}</span>
            </div>
            <ArrowRight className="text-gray-400" size={24} />
            <div className={clsx(
              'text-2xl font-bold px-4 py-2 rounded-lg border-2 border-dashed min-w-[100px]',
              selected
                ? submitted
                  ? selected === exercise.correctAnswer
                    ? 'border-green-400 bg-green-50 text-green-700'
                    : 'border-red-400 bg-red-50 text-red-700'
                  : `${caseColors.bg} ${caseColors.text} border-transparent`
                : 'border-gray-300 bg-gray-50 text-gray-400'
            )}>
              {selected || '?'}
            </div>
          </div>
        </div>

        {/* Options */}
        <div className="flex flex-wrap gap-3 justify-center">
          {shuffledOptions.map((option) => (
            <motion.button
              key={option}
              whileHover={!submitted ? { scale: 1.05 } : {}}
              whileTap={!submitted ? { scale: 0.95 } : {}}
              onClick={() => handleSelect(option)}
              disabled={disabled || submitted}
              className={clsx(
                'px-5 py-3 rounded-xl font-bold text-lg transition-all',
                'border-2 border-b-4',
                getOptionStyle(option)
              )}
            >
              {option}
            </motion.button>
          ))}
        </div>

        {/* Pattern hint */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-400">
            Pattern: <span className="font-medium">{exercise.patternName.replace(/_/g, ' ')}</span>
          </p>
        </div>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !selected || submitted}
        className={clsx(
          'mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all',
          selected && !submitted
            ? 'bg-primary-500 text-white hover:bg-primary-600 shadow-lg shadow-primary-200'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        )}
      >
        Check
      </button>
    </div>
  );
};

export default PatternApply;
