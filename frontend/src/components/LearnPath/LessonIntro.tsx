import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Clock, Zap } from 'lucide-react';
import { Mascot, ProgressRing } from '../Celebrations';
import { microcopy } from '../../lib/microcopy';

interface LessonIntroProps {
  title: string;
  description: string;
  content: { introduction?: string };
  vocabulary: Array<{ word: string; translation: string; audio?: string }>;
  moduleCount?: number;
  exerciseCount?: number;
  estimatedMinutes?: number;
  xpReward?: number;
  onStart: () => void;
}

export const LessonIntro: React.FC<LessonIntroProps> = ({
  title,
  description,
  vocabulary,
  moduleCount = 5,
  exerciseCount,
  estimatedMinutes = 5,
  xpReward = 15,
  onStart,
}) => {
  const hook = useMemo(() => microcopy.lessonHook(), []);
  const previewWords = vocabulary.slice(0, 3);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex-1 flex flex-col items-center justify-center p-6 max-w-lg mx-auto"
    >
      {/* Mascot with speech bubble */}
      <motion.div
        initial={{ scale: 0, rotate: -20 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
        className="relative mb-6"
      >
        <Mascot mood="happy" size={100} />
        
        {/* Speech bubble */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="absolute -right-4 -top-2 bg-white rounded-2xl px-4 py-2 shadow-lg border border-gray-100"
        >
          <div className="absolute -left-2 top-4 w-3 h-3 bg-white border-l border-b border-gray-100 transform rotate-45" />
          <p className="text-sm font-bold text-gray-700 whitespace-nowrap">{hook}</p>
        </motion.div>
      </motion.div>

      {/* Title */}
      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-3xl font-black text-gray-900 text-center mb-2"
      >
        {title}
      </motion.h1>

      {/* Description */}
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-gray-500 text-center mb-6"
      >
        {description}
      </motion.p>

      {/* Stats row */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="flex items-center gap-6 mb-8"
      >
        <div className="flex items-center gap-2 text-gray-500">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
            <Clock size={16} className="text-gray-400" />
          </div>
          <span className="text-sm font-medium">{estimatedMinutes} min</span>
        </div>
        
        <div className="flex items-center gap-2 text-gray-500">
          <ProgressRing progress={0} size={32} strokeWidth={3} color="#58cc02" bgColor="#e5e7eb">
            <span className="text-[10px] font-bold text-gray-600">{moduleCount}</span>
          </ProgressRing>
          <span className="text-sm font-medium">modules</span>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-yellow-100 flex items-center justify-center">
            <Zap size={16} className="text-yellow-500" />
          </div>
          <span className="text-sm font-bold text-yellow-600">+{xpReward} XP</span>
        </div>
      </motion.div>

      {/* Word preview (if vocabulary available) */}
      {previewWords.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="w-full mb-8"
        >
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 text-center">
            Words you'll learn
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {previewWords.map((word, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 + i * 0.1 }}
                className="bg-white rounded-xl px-4 py-2 border-2 border-gray-200 shadow-sm"
              >
                <span className="font-bold text-primary-700">{word.word}</span>
                <span className="text-gray-400 mx-2">·</span>
                <span className="text-gray-600">{word.translation}</span>
              </motion.div>
            ))}
            {vocabulary.length > 3 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.8 }}
                className="bg-gray-100 rounded-xl px-4 py-2 text-gray-500 font-medium"
              >
                +{vocabulary.length - 3} more
              </motion.div>
            )}
          </div>
        </motion.div>
      )}

      {/* Start Button */}
      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onStart}
        className="w-full bg-[#58cc02] text-white font-bold py-4 px-8 rounded-2xl hover:bg-[#4db302] transition-all shadow-lg shadow-green-200 border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px] flex items-center justify-center gap-3 text-lg"
      >
        Start Lesson
        <ArrowRight size={22} />
      </motion.button>

      {/* Skip option for returning users */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600 font-medium"
      >
        Already know this? Take a test
      </motion.button>
    </motion.div>
  );
};
