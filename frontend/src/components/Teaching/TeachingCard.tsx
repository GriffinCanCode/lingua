import React from 'react';
import { motion } from 'framer-motion';
import { Lightbulb, Volume2, CheckCircle2, Info, Brain, CheckCheck, Shuffle, AlertTriangle } from 'lucide-react';
import type { TeachingContent, WordIntroContent, SummaryContent, ExplanationContent, TipContent, CultureNoteContent, EnglishComparisonContent } from '../../types/teaching';
import { PatternTable } from './PatternTable';
import { EtymologyCard } from './EtymologyCard';
import { MorphologyPattern } from './MorphologyPattern';
import { ReadingPassageCard } from './ReadingPassageCard';

interface TeachingCardProps {
  content: TeachingContent;
  onPlayAudio?: (url: string) => void;
}

const ExplanationCard: React.FC<{ content: ExplanationContent }> = ({ content }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="w-full bg-white rounded-2xl p-6 border border-gray-200 shadow-sm"
  >
    <div className="flex items-center gap-3 mb-4">
      <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
        <Info size={20} className="text-white" />
      </div>
      <h3 className="font-bold text-gray-800 text-lg">{content.title}</h3>
    </div>
    <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
      {content.content}
    </div>
  </motion.div>
);

const TipCard: React.FC<{ content: TipContent }> = ({ content }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="w-full bg-amber-50 border border-amber-200 rounded-2xl p-5 flex gap-4"
  >
    <div className="w-10 h-10 rounded-xl bg-amber-400 flex items-center justify-center flex-shrink-0">
      <Lightbulb size={20} className="text-white" />
    </div>
    <p className="text-amber-900 font-medium">{content.content}</p>
  </motion.div>
);

const CultureCard: React.FC<{ content: CultureNoteContent }> = ({ content }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="w-full bg-gradient-to-br from-purple-50 via-pink-50 to-red-50 rounded-2xl p-6 border border-purple-200 shadow-sm"
  >
    <div className="flex items-center gap-3 mb-4">
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-red-500 flex items-center justify-center text-2xl">
        {content.emoji || '🇷🇺'}
      </div>
      <h3 className="font-bold text-gray-800 text-lg">{content.title}</h3>
    </div>
    <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap mb-3">
      {content.content}
    </div>
    {content.funFact && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-4 p-3 bg-white/60 rounded-xl border border-purple-100"
      >
        <p className="text-sm text-purple-800 font-medium">
          <span className="mr-2">✨</span>
          {content.funFact}
        </p>
      </motion.div>
    )}
  </motion.div>
);

interface WordIntroCardProps {
  content: WordIntroContent;
  onPlayAudio?: (url: string) => void;
}

const WordIntroCard: React.FC<WordIntroCardProps> = ({ content, onPlayAudio }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="w-full"
  >
    <div className="grid gap-4">
      {content.words.map((item, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.1 }}
          className="bg-white rounded-2xl p-5 border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-3xl font-black text-primary-700">{item.word}</span>
            {item.audio && onPlayAudio && (
              <button
                onClick={() => onPlayAudio(item.audio!)}
                className="p-2 rounded-full bg-primary-100 text-primary-600 hover:bg-primary-200 transition-colors"
              >
                <Volume2 size={20} />
              </button>
            )}
          </div>
          <p className="text-gray-600 font-medium">{item.translation}</p>
          {item.note && (
            <p className="mt-2 text-sm text-gray-500 italic">{item.note}</p>
          )}
          {item.mnemonic && (
            <div className="mt-2 flex items-center gap-1.5 text-sm text-indigo-600">
              <Brain size={14} className="flex-shrink-0" />
              <span>{item.mnemonic}</span>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  </motion.div>
);

const COMPARISON_STYLES = {
  similar: {
    bg: 'bg-gradient-to-br from-emerald-50 to-green-50',
    border: 'border-emerald-200',
    icon: CheckCheck,
    iconBg: 'bg-emerald-500',
    label: '✓ Like English',
    labelColor: 'text-emerald-700',
    textColor: 'text-emerald-900',
  },
  different: {
    bg: 'bg-gradient-to-br from-blue-50 to-indigo-50',
    border: 'border-blue-200',
    icon: Shuffle,
    iconBg: 'bg-blue-500',
    label: '≠ Unlike English',
    labelColor: 'text-blue-700',
    textColor: 'text-blue-900',
  },
  trap: {
    bg: 'bg-gradient-to-br from-red-50 to-orange-50',
    border: 'border-red-200',
    icon: AlertTriangle,
    iconBg: 'bg-red-500',
    label: '⚠️ English Speaker Trap',
    labelColor: 'text-red-700',
    textColor: 'text-red-900',
  },
} as const;

const EnglishComparisonCard: React.FC<{ content: EnglishComparisonContent }> = ({ content }) => {
  const style = COMPARISON_STYLES[content.comparison_type];
  const Icon = style.icon;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`w-full ${style.bg} rounded-2xl p-6 border ${style.border} shadow-sm`}
    >
      <div className="flex items-center gap-3 mb-1">
        <div className={`w-10 h-10 rounded-xl ${style.iconBg} flex items-center justify-center`}>
          <Icon size={20} className="text-white" />
        </div>
        <div>
          <span className={`text-xs font-semibold uppercase tracking-wide ${style.labelColor}`}>
            {style.label}
          </span>
          <h3 className="font-bold text-gray-800 text-lg -mt-0.5">{content.title}</h3>
        </div>
      </div>
      <div className={`prose prose-sm max-w-none ${style.textColor} whitespace-pre-wrap mt-3`}>
        {content.content}
      </div>
      {content.examples && content.examples.length > 0 && (
        <div className="mt-4 space-y-2">
          {content.examples.map((ex, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="p-3 bg-white/60 rounded-xl border border-white/80"
            >
              <div className="flex items-baseline gap-2">
                <span className="font-bold text-gray-800">{ex.ru}</span>
                <span className="text-gray-400">→</span>
                <span className="text-gray-600">{ex.en}</span>
              </div>
              {ex.note && <p className="text-xs text-gray-500 mt-1 italic">{ex.note}</p>}
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
};

const SummaryCard: React.FC<{ content: SummaryContent }> = ({ content }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="w-full bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-6 border border-green-200"
  >
    <div className="flex items-center gap-3 mb-5">
      <div className="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center">
        <CheckCircle2 size={20} className="text-white" />
      </div>
      <h3 className="font-bold text-gray-800 text-lg">{content.title}</h3>
    </div>
    <ul className="space-y-3">
      {content.points.map((point, idx) => (
        <motion.li
          key={idx}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.1 }}
          className="flex items-start gap-3"
        >
          <span className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
            ✓
          </span>
          <span className="text-gray-700">{point}</span>
        </motion.li>
      ))}
    </ul>
  </motion.div>
);

export const TeachingCard: React.FC<TeachingCardProps> = ({ content, onPlayAudio }) => {
  switch (content.type) {
    case 'explanation':
      return <ExplanationCard content={content} />;
    case 'pattern_table':
      return <PatternTable content={content} />;
    case 'etymology':
      return <EtymologyCard content={content} />;
    case 'morphology_pattern':
      return <MorphologyPattern content={content} />;
    case 'tip':
      return <TipCard content={content} />;
    case 'word_intro':
      return <WordIntroCard content={content} onPlayAudio={onPlayAudio} />;
    case 'summary':
      return <SummaryCard content={content} />;
    case 'culture_note':
      return <CultureCard content={content} />;
    case 'english_comparison':
      return <EnglishComparisonCard content={content} />;
    case 'reading_passage':
      return <ReadingPassageCard content={content} />;
    default:
      return null;
  }
};
