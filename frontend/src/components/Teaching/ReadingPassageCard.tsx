import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, Check, RotateCcw } from 'lucide-react';
import clsx from 'clsx';
import type { ReadingPassageContent, ReadingLevel } from '../../types/teaching';

const LEVEL_STYLES: Record<ReadingLevel, { bg: string; text: string; label: string }> = {
  beginner: { bg: 'bg-green-100', text: 'text-green-700', label: 'Beginner' },
  intermediate: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Intermediate' },
  advanced: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Advanced' },
};

interface PassageLineProps {
  ru: string;
  en: string;
  isRevealed: boolean;
  onReveal: () => void;
  index: number;
}

const PassageLine: React.FC<PassageLineProps> = ({ ru, en, isRevealed, onReveal, index }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: index * 0.05 }}
    onClick={onReveal}
    className={clsx(
      "p-4 rounded-xl cursor-pointer transition-all",
      isRevealed
        ? "bg-amber-50/50 border border-amber-200/50"
        : "bg-white hover:bg-amber-50/30 border border-transparent hover:border-amber-200/30 hover:shadow-sm"
    )}
  >
    <div className="flex items-start gap-3">
      {/* Reveal indicator */}
      <div className={clsx(
        "w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors",
        isRevealed ? "bg-green-500" : "bg-gray-200"
      )}>
        {isRevealed ? (
          <Check size={14} className="text-white" />
        ) : (
          <span className="w-2 h-2 rounded-full bg-gray-400" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        {/* Russian text - always visible */}
        <p className="text-xl font-medium text-gray-900 leading-relaxed">{ru}</p>

        {/* English translation - animated reveal */}
        <AnimatePresence>
          {isRevealed && (
            <motion.p
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: 'auto', marginTop: 8 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              transition={{ duration: 0.2 }}
              className="text-gray-500 text-base overflow-hidden"
            >
              {en}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>

    {/* Tap hint for unrevealed */}
    {!isRevealed && (
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 + index * 0.05 }}
        className="text-xs text-gray-400 mt-2 ml-9"
      >
        Tap to reveal translation
      </motion.p>
    )}
  </motion.div>
);

interface ReadingPassageCardProps {
  content: ReadingPassageContent;
  onComplete?: () => void;
}

export const ReadingPassageCard: React.FC<ReadingPassageCardProps> = ({ content, onComplete }) => {
  const [revealedLines, setRevealedLines] = useState<Set<number>>(new Set());
  const level = content.level || 'beginner';
  const levelStyle = LEVEL_STYLES[level];

  const revealedCount = revealedLines.size;
  const totalLines = content.paragraphs.length;
  const allRevealed = revealedCount === totalLines;
  const progress = totalLines > 0 ? (revealedCount / totalLines) * 100 : 0;

  const handleReveal = (idx: number) => {
    if (revealedLines.has(idx)) return;
    
    const newRevealed = new Set(revealedLines);
    newRevealed.add(idx);
    setRevealedLines(newRevealed);

    if (newRevealed.size === totalLines) {
      onComplete?.();
    }
  };

  const handleReset = () => setRevealedLines(new Set());

  const handleRevealAll = () => {
    setRevealedLines(new Set(content.paragraphs.map((_, i) => i)));
    onComplete?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 rounded-2xl border border-amber-200 shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-5 border-b border-amber-200/50 bg-white/40">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-sm">
              <BookOpen size={22} className="text-white" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 text-lg">{content.title}</h3>
              <span className={clsx("text-xs font-semibold px-2 py-0.5 rounded-full", levelStyle.bg, levelStyle.text)}>
                {levelStyle.label}
              </span>
            </div>
          </div>

          {/* Progress */}
          <div className="text-right">
            <p className="text-sm font-medium text-gray-600">
              {revealedCount} / {totalLines}
            </p>
            <div className="w-20 h-1.5 bg-amber-200 rounded-full mt-1 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Passage lines */}
      <div className="p-4 space-y-2">
        {content.paragraphs.map((para, idx) => (
          <PassageLine
            key={idx}
            ru={para.ru}
            en={para.en}
            isRevealed={revealedLines.has(idx)}
            onReveal={() => handleReveal(idx)}
            index={idx}
          />
        ))}
      </div>

      {/* Comprehension tip - shows when all revealed */}
      <AnimatePresence>
        {allRevealed && content.comprehension_tip && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 pb-5 overflow-hidden"
          >
            <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
              <p className="text-green-800 text-sm font-medium">
                <span className="mr-2">💡</span>
                {content.comprehension_tip}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer actions */}
      <div className="px-6 pb-5 flex items-center justify-between">
        {allRevealed ? (
          <button
            onClick={handleReset}
            className="flex items-center gap-2 text-sm font-medium text-amber-700 hover:text-amber-900 transition-colors"
          >
            <RotateCcw size={16} />
            Read Again
          </button>
        ) : (
          <button
            onClick={handleRevealAll}
            className="text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
          >
            Reveal all
          </button>
        )}

        {allRevealed && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 text-green-600 font-semibold"
          >
            <Check size={18} />
            Complete!
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
