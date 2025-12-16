import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { microcopy } from '../../lib/microcopy';
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

  const prompt = useMemo(() => microcopy.exercisePrompt('matching'), []);

  const shuffledRight = useMemo(() =>
    [...exercise.pairs].sort(() => Math.random() - 0.5),
    [exercise.pairs]
  );

  const handleLeftClick = useCallback((id: string) => {
    if (disabled || state.matched.has(id)) return;

    setState(prev => {
      if (prev.rightSelected) {
        const leftPair = exercise.pairs.find(p => p.id === id);
        const rightPair = exercise.pairs.find(p => p.id === prev.rightSelected);

        if (leftPair && rightPair && leftPair.id === rightPair.id) {
          const newMatched = new Set(prev.matched).add(id);
          return { ...prev, leftSelected: null, rightSelected: null, matched: newMatched, incorrect: new Set() };
        } else {
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
      if (prev.leftSelected) {
        const leftPair = exercise.pairs.find(p => p.id === prev.leftSelected);
        const rightPair = exercise.pairs.find(p => p.id === id);

        if (leftPair && rightPair && leftPair.id === rightPair.id) {
          const newMatched = new Set(prev.matched).add(id);
          return { ...prev, leftSelected: null, rightSelected: null, matched: newMatched, incorrect: new Set() };
        } else {
          const newIncorrect = new Set([prev.leftSelected, id]);
          setTimeout(() => setState(s => ({ ...s, incorrect: new Set(), leftSelected: null, rightSelected: null })), 600);
          return { ...prev, rightSelected: id, incorrect: newIncorrect };
        }
      }
      return { ...prev, rightSelected: id, incorrect: new Set() };
    });
  }, [disabled, state.matched, exercise.pairs]);

  const allMatched = state.matched.size === exercise.pairs.length;

  useEffect(() => {
    if (allMatched) {
      setTimeout(() => onSubmit(Array.from(state.matched)), 500);
    }
  }, [allMatched, onSubmit, state.matched]);

  return (
    <div className="flex flex-col h-full">
      {/* Prompt */}
      <div className="text-center mb-6">
        <p className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-2">
          {prompt}
        </p>
        <p className="text-gray-500">
          Tap matching pairs to connect them
        </p>
      </div>

      {/* Matching Grid */}
      <div className="flex-1 flex gap-6 justify-center items-start">
        {/* Left Column */}
        <div className="flex flex-col gap-3">
          <AnimatePresence>
            {exercise.pairs.map((pair, idx) => (
              <motion.button
                key={`left-${pair.id}`}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{
                  opacity: state.matched.has(pair.id) ? 0 : 1,
                  scale: state.matched.has(pair.id) ? 0.8 : 1,
                  x: 0,
                }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
                onClick={() => handleLeftClick(pair.id)}
                disabled={disabled || state.matched.has(pair.id)}
                className={clsx(
                  "py-3 px-5 rounded-xl font-medium text-lg transition-all border-2 border-b-4 min-w-[140px] active:border-b-2 active:translate-y-[2px]",
                  state.matched.has(pair.id) && "invisible",
                  state.incorrect.has(pair.id)
                    ? "bg-red-100 border-red-300 text-red-700"
                    : state.leftSelected === pair.id
                    ? "bg-[#58cc02] border-[#4db302] text-white"
                    : "bg-white border-gray-200 text-gray-800 hover:border-primary-300"
                )}
              >
                {pair.left}
              </motion.button>
            ))}
          </AnimatePresence>
        </div>

        {/* Connector line area */}
        <div className="w-8 flex items-center justify-center">
          <div className="h-full w-0.5 bg-gray-200 rounded-full" />
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-3">
          <AnimatePresence>
            {shuffledRight.map((pair, idx) => (
              <motion.button
                key={`right-${pair.id}`}
                layout
                initial={{ opacity: 0, x: 20 }}
                animate={{
                  opacity: state.matched.has(pair.id) ? 0 : 1,
                  scale: state.matched.has(pair.id) ? 0.8 : 1,
                  x: 0,
                }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
                onClick={() => handleRightClick(pair.id)}
                disabled={disabled || state.matched.has(pair.id)}
                className={clsx(
                  "py-3 px-5 rounded-xl font-medium text-lg transition-all border-2 border-b-4 min-w-[140px] active:border-b-2 active:translate-y-[2px]",
                  state.matched.has(pair.id) && "invisible",
                  state.incorrect.has(pair.id)
                    ? "bg-red-100 border-red-300 text-red-700"
                    : state.rightSelected === pair.id
                    ? "bg-[#58cc02] border-[#4db302] text-white"
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
      <div className="mt-8">
        <div className="flex items-center justify-between text-sm text-gray-500 mb-2">
          <span>Progress</span>
          <span className="font-bold">{state.matched.size} / {exercise.pairs.length}</span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${(state.matched.size / exercise.pairs.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
    </div>
  );
};

export default Matching;
