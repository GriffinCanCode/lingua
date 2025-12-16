import React from 'react';
import { motion } from 'framer-motion';
import { Puzzle, ArrowRight } from 'lucide-react';
import type { MorphologyPatternContent } from '../../types/teaching';

interface MorphologyPatternProps {
  content: MorphologyPatternContent;
}

export const MorphologyPattern: React.FC<MorphologyPatternProps> = ({ content }) => {
  const { title, formula, examples, rule } = content;

  // Parse formula to highlight placeholders
  const renderFormula = (f: string) => {
    const parts = f.split(/(\{[^}]+\})/);
    return parts.map((part, i) => {
      if (part.startsWith('{') && part.endsWith('}')) {
        return (
          <span key={i} className="inline-block px-2 py-1 mx-1 bg-emerald-100 text-emerald-700 rounded-lg font-bold">
            {part.slice(1, -1)}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-gradient-to-br from-emerald-50 to-teal-50 rounded-2xl p-6 border border-emerald-100"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center">
          <Puzzle size={20} className="text-white" />
        </div>
        <div>
          <h3 className="font-bold text-gray-800">{title}</h3>
          <span className="text-xs text-emerald-600 font-medium">Grammar Pattern</span>
        </div>
      </div>

      {/* Formula */}
      <div className="bg-white rounded-xl p-4 mb-5 text-center border border-emerald-100">
        <span className="text-lg font-medium text-gray-700">
          {renderFormula(formula)}
        </span>
      </div>

      {/* Examples */}
      <div className="space-y-3">
        {examples.map((ex, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="flex items-center gap-3 p-3 bg-white/70 rounded-xl border border-emerald-100"
          >
            <span className="text-lg font-bold text-emerald-700">{ex.ru}</span>
            <ArrowRight size={16} className="text-gray-400 flex-shrink-0" />
            <span className="text-gray-600">{ex.en}</span>
          </motion.div>
        ))}
      </div>

      {/* Rule explanation */}
      {rule && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-5 p-4 bg-emerald-100/50 rounded-xl text-sm text-emerald-800 font-medium border border-emerald-200"
        >
          📝 {rule}
        </motion.div>
      )}
    </motion.div>
  );
};
