import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { PatternFillExercise, ExerciseComponentProps, GrammaticalCase } from '../../types/exercises';

const CASE_LABELS: Record<GrammaticalCase, string> = {
  nominative: 'Nominative',
  genitive: 'Genitive',
  dative: 'Dative',
  accusative: 'Accusative',
  instrumental: 'Instrumental',
  prepositional: 'Prepositional',
};

const CASE_HINTS: Record<GrammaticalCase, string> = {
  nominative: 'кто? что? (who? what?)',
  genitive: 'кого? чего? (of whom? of what?)',
  dative: 'кому? чему? (to whom? to what?)',
  accusative: 'кого? что? (whom? what?)',
  instrumental: 'кем? чем? (with whom? with what?)',
  prepositional: 'о ком? о чём? (about whom? about what?)',
};

const CASE_COLORS: Record<GrammaticalCase, { bg: string; text: string; border: string }> = {
  nominative: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
  genitive: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-300' },
  dative: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-300' },
  accusative: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-300' },
  instrumental: { bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-300' },
  prepositional: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-300' },
};

export const PatternFill: React.FC<ExerciseComponentProps<PatternFillExercise>> = ({
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
        ? `${caseColors.bg} ${caseColors.text} border-2 ${caseColors.border}`
        : 'bg-white border-gray-200 text-gray-800 hover:border-gray-400';
    }

    if (option === exercise.correctEnding) {
      return 'bg-green-500 text-white border-green-600';
    }
    if (option === selected && option !== exercise.correctEnding) {
      return 'bg-red-500 text-white border-red-600';
    }
    return 'bg-gray-100 border-gray-200 text-gray-400';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-2">
          Select the correct ending
        </p>
        <div className={clsx(
          'inline-block px-3 py-1 rounded-full text-xs font-bold',
          caseColors.bg, caseColors.text
        )}>
          {CASE_LABELS[exercise.targetCase]} • {exercise.targetNumber}
        </div>
      </div>

      {/* Word display with stem + blank */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="mb-4">
          <p className="text-gray-500 text-sm mb-1">{exercise.translation}</p>
          <p className="text-gray-400 text-xs">{CASE_HINTS[exercise.targetCase]}</p>
        </div>

        {/* Stem + Ending visualization */}
        <div className="flex items-baseline justify-center mb-8">
          <span className="text-4xl md:text-5xl font-bold text-gray-600">{exercise.stem}</span>
          <span className={clsx(
            'text-4xl md:text-5xl font-bold px-3 py-1 min-w-[60px] rounded-lg border-2 border-dashed text-center',
            selected
              ? submitted
                ? selected === exercise.correctEnding
                  ? 'border-green-400 bg-green-100 text-green-700'
                  : 'border-red-400 bg-red-100 text-red-700'
                : `${caseColors.border} ${caseColors.bg} ${caseColors.text}`
              : 'border-gray-300 bg-gray-50 text-gray-400'
          )}>
            {selected || '?'}
          </span>
        </div>

        {/* Full form preview */}
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <span className="text-gray-500 text-sm">Result: </span>
            <span className="text-xl font-bold text-gray-800">
              {exercise.stem}{selected}
            </span>
          </motion.div>
        )}

        {/* Ending options */}
        <div className="flex flex-wrap gap-3 justify-center">
          {shuffledOptions.map((option) => (
            <motion.button
              key={option}
              whileHover={!submitted ? { scale: 1.05 } : {}}
              whileTap={!submitted ? { scale: 0.95 } : {}}
              onClick={() => handleSelect(option)}
              disabled={disabled || submitted}
              className={clsx(
                'px-6 py-3 rounded-xl font-mono font-bold text-xl transition-all',
                'border-2 border-b-4',
                getOptionStyle(option)
              )}
            >
              -{option || '∅'}
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

export default PatternFill;
