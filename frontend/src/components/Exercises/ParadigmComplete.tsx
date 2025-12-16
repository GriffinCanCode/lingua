import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { ParadigmCompleteExercise, ExerciseComponentProps, GrammaticalCase, CaseConfig } from '../../types/exercises';

const CASE_ORDER: GrammaticalCase[] = ['nominative', 'genitive', 'dative', 'accusative', 'instrumental', 'prepositional'];

// Fallback case colors when API data not available
const DEFAULT_CASE_COLORS: Record<GrammaticalCase, string> = {
  nominative: 'bg-blue-50 text-blue-700',
  genitive: 'bg-green-50 text-green-700',
  dative: 'bg-orange-50 text-orange-700',
  accusative: 'bg-purple-50 text-purple-700',
  instrumental: 'bg-pink-50 text-pink-700',
  prepositional: 'bg-cyan-50 text-cyan-700',
};

export const ParadigmComplete: React.FC<ExerciseComponentProps<ParadigmCompleteExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
  grammarConfig,
}) => {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const blanks = exercise.blankIndices;
  const allFilled = blanks.every(idx => answers[idx]);

  // Build case colors from grammar config or use defaults
  const caseColors = useMemo(() => {
    if (!grammarConfig) return DEFAULT_CASE_COLORS;
    return grammarConfig.cases.reduce((acc, c) => ({
      ...acc,
      [c.id]: `${c.color.bg} ${c.color.text}`,
    }), {} as Record<string, string>);
  }, [grammarConfig]);

  const handleCellClick = useCallback((idx: number, option: string) => {
    if (disabled || submitted || !exercise.cells[idx].isBlank) return;
    setAnswers(prev => ({ ...prev, [idx]: option }));
  }, [disabled, submitted, exercise.cells]);

  const handleSubmit = useCallback(() => {
    if (!allFilled) return;
    setSubmitted(true);
    const answerArray = blanks.map(idx => answers[idx]);
    setTimeout(() => onSubmit(answerArray), 500);
  }, [allFilled, blanks, answers, onSubmit]);

  const sortedCells = [...exercise.cells].sort((a, b) =>
    CASE_ORDER.indexOf(a.case as GrammaticalCase) - CASE_ORDER.indexOf(b.case as GrammaticalCase)
  );

  const getCellStyle = (cell: typeof exercise.cells[0], idx: number) => {
    const originalIdx = exercise.cells.indexOf(cell);
    const isBlank = cell.isBlank;
    const answer = answers[originalIdx];

    if (!isBlank) {
      return 'bg-gray-50 text-gray-700';
    }

    if (!submitted) {
      const colorClass = caseColors[cell.case as GrammaticalCase] || DEFAULT_CASE_COLORS[cell.case as GrammaticalCase];
      return answer
        ? `${colorClass} font-bold`
        : 'bg-white border-2 border-dashed border-gray-300 text-gray-400';
    }

    const isCorrect = answer === cell.form;
    return isCorrect
      ? 'bg-green-100 text-green-700 font-bold'
      : 'bg-red-100 text-red-700 font-bold';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="text-center mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-2">
          Complete the paradigm
        </p>
        <h3 className="text-2xl font-bold text-gray-900">{exercise.lemma}</h3>
        <p className="text-gray-500">{exercise.translation}</p>
        <div className="mt-2 flex items-center justify-center gap-2">
          <span className={clsx(
            'px-2 py-1 rounded text-xs font-bold',
            exercise.gender === 'masculine' && 'bg-blue-100 text-blue-700',
            exercise.gender === 'feminine' && 'bg-pink-100 text-pink-700',
            exercise.gender === 'neuter' && 'bg-gray-100 text-gray-700',
          )}>
            {exercise.gender}
          </span>
          <span className="px-2 py-1 rounded text-xs font-bold bg-indigo-100 text-indigo-700">
            {exercise.patternName.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      {/* Paradigm Table */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="w-full max-w-md overflow-hidden rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-bold text-gray-500 uppercase">Case</th>
                <th className="px-4 py-2 text-center text-xs font-bold text-gray-500 uppercase">Form</th>
              </tr>
            </thead>
            <tbody>
              {sortedCells.map((cell, displayIdx) => {
                const originalIdx = exercise.cells.indexOf(cell);
                const bgClass = (caseColors[cell.case as GrammaticalCase] || DEFAULT_CASE_COLORS[cell.case as GrammaticalCase])?.split(' ')[0] || 'bg-gray-50';
                return (
                  <tr key={displayIdx} className="border-t border-gray-100">
                    <td className={clsx('px-4 py-3 font-medium capitalize', bgClass)}>
                      {cell.case}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <motion.div className={clsx('px-3 py-2 rounded-lg text-lg transition-all', getCellStyle(cell, originalIdx))}>
                        {cell.isBlank ? (answers[originalIdx] || '___') : cell.form}
                      </motion.div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Word Bank */}
        <div className="mt-8 flex flex-wrap gap-2 justify-center">
          {exercise.options.map((option) => {
            const isUsed = Object.values(answers).includes(option);
            return (
              <motion.button
                key={option}
                whileHover={!submitted && !isUsed ? { scale: 1.05 } : {}}
                whileTap={!submitted && !isUsed ? { scale: 0.95 } : {}}
                onClick={() => {
                  const firstEmpty = blanks.find(idx => !answers[idx]);
                  if (firstEmpty !== undefined) {
                    handleCellClick(firstEmpty, option);
                  }
                }}
                disabled={disabled || submitted || isUsed}
                className={clsx(
                  'px-4 py-2 rounded-lg font-medium transition-all border-2',
                  isUsed
                    ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                    : 'bg-white text-gray-800 border-gray-200 hover:border-primary-400 hover:bg-primary-50'
                )}
              >
                {option}
              </motion.button>
            );
          })}
        </div>

        {/* Clear button */}
        {Object.keys(answers).length > 0 && !submitted && (
          <button onClick={() => setAnswers({})} className="mt-4 text-sm text-gray-500 hover:text-gray-700">
            Clear all
          </button>
        )}
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={disabled || !allFilled || submitted}
        className={clsx(
          'mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all',
          allFilled && !submitted
            ? 'bg-primary-500 text-white hover:bg-primary-600 shadow-lg shadow-primary-200'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        )}
      >
        Check
      </button>
    </div>
  );
};

export default ParadigmComplete;
