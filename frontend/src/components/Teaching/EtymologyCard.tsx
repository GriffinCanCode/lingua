import React from 'react';
import { motion } from 'framer-motion';
import { BookOpen, ArrowRight, Globe2 } from 'lucide-react';
import clsx from 'clsx';
import type { EtymologyContent, EtymologyConnection } from '../../types/teaching';

interface EtymologyCardProps {
  content: EtymologyContent;
}

const RELATION_COLORS: Record<EtymologyConnection['relation'], { bg: string; text: string; border: string }> = {
  cognate: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  ancestor: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
  cousin: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' },
  descendant: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  borrowing: { bg: 'bg-pink-100', text: 'text-pink-700', border: 'border-pink-300' },
};

const RELATION_LABELS: Record<EtymologyConnection['relation'], string> = {
  cognate: 'Same root',
  ancestor: 'Parent',
  cousin: 'Related',
  descendant: 'Child',
  borrowing: 'Borrowed',
};

export const EtymologyCard: React.FC<EtymologyCardProps> = ({ content }) => {
  const { title, word, connections, insight } = content;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-6 border border-indigo-100"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-indigo-500 flex items-center justify-center">
          <BookOpen size={20} className="text-white" />
        </div>
        <div>
          <h3 className="font-bold text-gray-800">{title}</h3>
          <span className="text-xs text-indigo-600 font-medium">Word Family</span>
        </div>
      </div>

      {/* Central word */}
      <div className="text-center mb-6">
        <motion.span
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          className="inline-block text-4xl font-black text-indigo-700"
        >
          {word}
        </motion.span>
      </div>

      {/* Connections */}
      <div className="space-y-3">
        {connections.map((conn, idx) => {
          const colors = RELATION_COLORS[conn.relation];
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={clsx(
                "flex items-center gap-3 p-3 rounded-xl border",
                colors.bg, colors.border
              )}
            >
              <ArrowRight size={16} className={colors.text} />
              <span className={clsx("font-bold text-lg", colors.text)}>{conn.word}</span>
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Globe2 size={12} />
                {conn.lang}
              </span>
              <span className={clsx(
                "ml-auto text-xs px-2 py-0.5 rounded-full font-medium",
                colors.bg, colors.text
              )}>
                {RELATION_LABELS[conn.relation]}
              </span>
            </motion.div>
          );
        })}
      </div>

      {/* Insight */}
      {insight && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-5 p-4 bg-white/70 rounded-xl text-sm text-gray-700 italic border border-indigo-100"
        >
          💡 {insight}
        </motion.div>
      )}
    </motion.div>
  );
};
