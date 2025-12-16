import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles } from 'lucide-react';

interface LessonIntroProps {
  title: string;
  description: string;
  content: { introduction?: string };
  vocabulary: Array<{ word: string; translation: string; audio?: string }>;
  onStart: () => void;
}

export const LessonIntro: React.FC<LessonIntroProps> = ({ title, description, onStart }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex-1 flex items-center justify-center p-6"
    >
      <div className="text-center max-w-md">
        {/* Icon */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', delay: 0.1, stiffness: 200 }}
          className="w-24 h-24 bg-gradient-to-br from-primary-400 to-primary-600 rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-xl shadow-primary-200"
        >
          <Sparkles size={48} className="text-white" />
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-3xl font-black text-gray-900 mb-3"
        >
          {title}
        </motion.h1>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-gray-500 mb-10"
        >
          {description}
        </motion.p>

        {/* Start Button */}
        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onStart}
          className="w-full bg-[#58cc02] text-white font-bold py-4 px-8 rounded-2xl hover:bg-[#4db302] transition-all shadow-lg shadow-green-200 flex items-center justify-center gap-3 text-lg"
        >
          Start Lesson
          <ArrowRight size={22} />
        </motion.button>
      </div>
    </motion.div>
  );
};
