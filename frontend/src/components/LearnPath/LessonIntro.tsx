import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Clock, Zap, Target } from 'lucide-react';

interface LessonIntroProps {
  title: string;
  description: string;
  content: { introduction?: string };
  vocabulary: Array<{ word: string; translation: string; audio?: string }>;
  onStart: () => void;
}

export const LessonIntro: React.FC<LessonIntroProps> = ({ title, description, content, vocabulary, onStart }) => {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-lg mx-auto mt-8">
      <div className="bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="bg-gradient-to-br from-primary-500 to-primary-600 p-8 text-center text-white">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="w-20 h-20 bg-white/20 backdrop-blur rounded-full flex items-center justify-center mx-auto mb-4"
          >
            <Target size={40} />
          </motion.div>
          <h1 className="text-2xl font-black mb-2">{title}</h1>
          <p className="text-white/80">{description}</p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Stats */}
          <div className="flex justify-center gap-6 mb-6 py-4 border-b border-gray-100">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-primary-600 mb-1">
                <Zap size={18} />
                <span className="font-bold">+{vocabulary.length * 10}</span>
              </div>
              <span className="text-xs text-gray-500">XP</span>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-gray-700 mb-1">
                <Clock size={18} />
                <span className="font-bold">~5</span>
              </div>
              <span className="text-xs text-gray-500">Minutes</span>
            </div>
            <div className="text-center">
              <div className="font-bold text-gray-700 mb-1">{vocabulary.length}</div>
              <span className="text-xs text-gray-500">Words</span>
            </div>
          </div>

          {/* Introduction Text */}
          {content.introduction && (
            <div className="bg-blue-50 rounded-xl p-4 mb-6 text-sm text-blue-800">
              {content.introduction}
            </div>
          )}

          {/* Word Preview */}
          {vocabulary.length > 0 && (
            <div className="mb-6">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">You'll learn:</p>
              <div className="flex flex-wrap gap-2">
                {vocabulary.slice(0, 6).map((item, idx) => (
                  <span key={idx} className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-full">
                    {item.word}
                  </span>
                ))}
                {vocabulary.length > 6 && (
                  <span className="px-3 py-1.5 bg-gray-100 text-gray-500 text-sm rounded-full">
                    +{vocabulary.length - 6} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Start Button */}
          <button
            onClick={onStart}
            className="w-full bg-green-500 text-white font-bold py-4 px-8 rounded-xl hover:bg-green-600 transition-all shadow-lg shadow-green-200 flex items-center justify-center gap-2 text-lg"
          >
            Start <ArrowRight size={20} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
