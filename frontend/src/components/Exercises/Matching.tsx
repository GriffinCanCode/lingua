import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { MatchingExercise, ExerciseComponentProps } from '../../types/exercises';

interface MatchState {
  leftSelected: string | null;
  rightSelected: string | null;
  matched: Set<string>;
  incorrect: Set<string>;
}

export const Matching: React.FC<ExerciseComponentProps<MatchingExercise>> = ({
  exercise,
  onSubmit,
  disabled = false,
}) => {
  const [state, setState] = useState<MatchState>({
    leftSelected: null,
    rightSelected: null,
    matched: new Set(),
    incorrect: new Set(),
  });

  // Shuffle right column on mount
  const shuffledRight = useMemo(() =>
    [...exercise.pairs].sort(() => Math.random() - 0.5),
    [exercise.pairs]
  );

  const handleLeftClick = useCallback((id: string) => {
    if (disabled || state.matched.has(id)) return;

    setState(prev => {
      // If right is already selected, try to match
      if (prev.rightSelected) {
        const leftPair = exercise.pairs.find(p => p.id === id);
        const rightPair = exercise.pairs.find(p => p.id === prev.rightSelected);

        if (leftPair && rightPair && leftPair.id === rightPair.id) {
          // Correct match
          const newMatched = new Set(prev.matched).add(id);
          return { ...prev, leftSelected: null, rightSelected: null, matched: newMatched, incorrect: new Set() };
        } else {
          // Wrong match
          const newIncorrect = new Set([id, prev.rightSelected]);
          setTimeout(() => setState(s => ({ ...s, incorrect: new Set(), leftSelected: null, rightSelected: null })), 600);
          return { ...prev, leftSelected: id, incorrect: newIncorrect };
        }
      }

      return { ...prev, leftSelected: id, incorrect: new Set() };
    });
  }, [disabled, state.matched, exercise.pairs]);

  const handleRightClick = useCallback((id: string) => {
    if (disabled || state.matched.has(id)) return;

    setState(prev => {
      // If left is already selected, try to match
      if (prev.leftSelected) {
        const leftPair = exercise.pairs.find(p => p.id === prev.leftSelected);
        const rightPair = exercise.pairs.find(p => p.id === id);

        if (leftPair && rightPair && leftPair.id === rightPair.id) {
          // Correct match
          const newMatched = new Set(prev.matched).add(id);
          return { ...prev, leftSelected: null, rightSelected: null, matched: newMatched, incorrect: new Set() };
        } else {
          // Wrong match
          const newIncorrect = new Set([prev.leftSelected, id]);
          setTimeout(() => setState(s => ({ ...s, incorrect: new Set(), leftSelected: null, rightSelected: null })), 600);
          return { ...prev, rightSelected: id, incorrect: newIncorrect };
        }
      }

      return { ...prev, rightSelected: id, incorrect: new Set() };
    });
  }, [disabled, state.matched, exercise.pairs]);

  // Auto-submit when all matched
  const allMatched = state.matched.size === exercise.pairs.length;

  React.useEffect(() => {
    if (allMatched) {
      setTimeout(() => onSubmit(Array.from(state.matched)), 500);
    }
  }, [allMatched, onSubmit, state.matched]);

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-4">
          Match the pairs
        </p>
        <p className="text-xl text-gray-600">
          Tap a word on the left, then its translation on the right
        </p>
      </div>

      {/* Matching Grid */}
      <div className="flex-1 flex gap-4 justify-center">
        {/* Left Column */}
        <div className="flex flex-col gap-3 w-40">
          <AnimatePresence>
            {exercise.pairs.map((pair) => (
              <motion.button
                key={`left-${pair.id}`}
                layout
                initial={{ opacity: 1 }}
                animate={{
                  opacity: state.matched.has(pair.id) ? 0 : 1,
                  scale: state.matched.has(pair.id) ? 0.8 : 1,
                }}
                transition={{ duration: 0.3 }}
                onClick={() => handleLeftClick(pair.id)}
                disabled={disabled || state.matched.has(pair.id)}
                className={clsx(
                  "py-3 px-4 rounded-xl font-medium text-lg transition-all border-2 border-b-4",
                  state.matched.has(pair.id) && "invisible",
                  state.incorrect.has(pair.id)
                    ? "bg-red-100 border-red-300 text-red-700 animate-shake"
                    : state.leftSelected === pair.id
                    ? "bg-primary-100 border-primary-400 text-primary-700"
                    : "bg-white border-gray-200 text-gray-800 hover:border-primary-300"
                )}
              >
                {pair.left}
              </motion.button>
            ))}
          </AnimatePresence>
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-3 w-40">
          <AnimatePresence>
            {shuffledRight.map((pair) => (
              <motion.button
                key={`right-${pair.id}`}
                layout
                initial={{ opacity: 1 }}
                animate={{
                  opacity: state.matched.has(pair.id) ? 0 : 1,
                  scale: state.matched.has(pair.id) ? 0.8 : 1,
                }}
                transition={{ duration: 0.3 }}
                onClick={() => handleRightClick(pair.id)}
                disabled={disabled || state.matched.has(pair.id)}
                className={clsx(
                  "py-3 px-4 rounded-xl font-medium text-lg transition-all border-2 border-b-4",
                  state.matched.has(pair.id) && "invisible",
                  state.incorrect.has(pair.id)
                    ? "bg-red-100 border-red-300 text-red-700"
                    : state.rightSelected === pair.id
                    ? "bg-primary-100 border-primary-400 text-primary-700"
                    : "bg-white border-gray-200 text-gray-800 hover:border-primary-300"
                )}
              >
                {pair.right}
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Progress */}
      <div className="mt-8 text-center">
        <p className="text-gray-500">
          {state.matched.size} / {exercise.pairs.length} matched
        </p>
        <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-green-500"
            initial={{ width: 0 }}
            animate={{ width: `${(state.matched.size / exercise.pairs.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default Matching;
