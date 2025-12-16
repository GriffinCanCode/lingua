import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Clock, Zap, BookOpen, Star } from 'lucide-react';
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

// Animated word preview card
const WordPreviewCard: React.FC<{
  word: string;
  translation: string;
  index: number;
}> = ({ word, translation, index }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.8, y: 20 }}
    animate={{ opacity: 1, scale: 1, y: 0 }}
    transition={{ delay: 0.4 + index * 0.1, type: 'spring', stiffness: 300 }}
    whileHover={{ scale: 1.05, y: -2 }}
    className="bg-white rounded-2xl px-5 py-3 border-2 border-gray-100 shadow-sm hover:shadow-md hover:border-primary-200 transition-all cursor-default"
  >
    <p className="font-bold text-lg text-primary-600">{word}</p>
    <p className="text-sm text-gray-500">{translation}</p>
  </motion.div>
);

// Stats pill
const StatPill: React.FC<{
  icon: React.ReactNode;
  label: string;
  color?: string;
}> = ({ icon, label, color = 'gray' }) => (
  <div className={`flex items-center gap-2 px-3 py-2 rounded-xl bg-${color}-100`}>
    {icon}
    <span className={`text-sm font-medium text-${color}-600`}>{label}</span>
  </div>
);

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
  const previewWords = vocabulary.slice(0, 4);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex-1 flex flex-col items-center justify-center p-6 max-w-lg mx-auto"
    >
      {/* Hero section with mascot */}
      <div className="relative mb-8">
        <motion.div
          initial={{ scale: 0, rotate: -20 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
        >
          <Mascot mood="encouraging" size={120} />
        </motion.div>
        
        {/* Speech bubble */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8, x: -20 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ delay: 0.3, type: 'spring' }}
          className="absolute -right-2 top-0 bg-white rounded-2xl px-4 py-2 shadow-lg border border-gray-100"
        >
          <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-l border-b border-gray-100 transform rotate-45" />
          <p className="text-sm font-bold text-gray-700 whitespace-nowrap">{hook}</p>
        </motion.div>
      </div>

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
        transition={{ delay: 0.25 }}
        className="text-gray-500 text-center mb-6 max-w-sm"
      >
        {description}
      </motion.p>

      {/* Stats row */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex flex-wrap items-center justify-center gap-3 mb-8"
      >
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-100">
          <Clock size={16} className="text-gray-500" />
          <span className="text-sm font-medium text-gray-600">{estimatedMinutes} min</span>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-primary-100">
          <ProgressRing progress={0} size={20} strokeWidth={2} color="#58cc02" bgColor="#d1fae5">
            <BookOpen size={10} className="text-primary-600" />
          </ProgressRing>
          <span className="text-sm font-medium text-primary-600">{moduleCount} modules</span>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-yellow-100">
          <Zap size={16} className="text-yellow-600" />
          <span className="text-sm font-bold text-yellow-600">+{xpReward} XP</span>
        </div>
      </motion.div>

      {/* Word preview */}
      {previewWords.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="w-full mb-8"
        >
          <div className="flex items-center justify-center gap-2 mb-4">
            <Star size={16} className="text-amber-500" />
            <p className="text-sm font-bold text-gray-500 uppercase tracking-wider">
              Words you'll learn
            </p>
          </div>
          
          <div className="flex flex-wrap justify-center gap-3">
            {previewWords.map((word, i) => (
              <WordPreviewCard
                key={i}
                word={word.word}
                translation={word.translation}
                index={i}
              />
            ))}
            {vocabulary.length > 4 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.8 }}
                className="flex items-center justify-center px-5 py-3 bg-gray-100 rounded-2xl"
              >
                <span className="text-sm font-bold text-gray-500">
                  +{vocabulary.length - 4} more
                </span>
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
        className="w-full bg-[#58cc02] text-white font-bold py-5 px-8 rounded-2xl hover:bg-[#4db302] transition-all shadow-xl shadow-green-200 border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px] flex items-center justify-center gap-3 text-lg"
      >
        Start Lesson
        <motion.div
          animate={{ x: [0, 4, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <ArrowRight size={24} />
        </motion.div>
      </motion.button>

      {/* Skip option */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600 font-medium transition-colors"
      >
        Already know this? Take a test
      </motion.button>
    </motion.div>
  );
};
