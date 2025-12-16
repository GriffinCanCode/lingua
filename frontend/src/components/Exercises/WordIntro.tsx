import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2, ChevronRight, Lightbulb, Check, BookOpen } from 'lucide-react';
import clsx from 'clsx';

export interface VocabWord {
  word: string;
  translation: string;
  transliteration?: string;
  audio?: string;
  hints?: string[];
  icon?: string;
  gender?: string;
  stem?: string;
  pattern?: string;
}

// Pattern display names
const PATTERN_NAMES: Record<string, string> = {
  fem_a_declension: 'Type I (Fem -а)',
  masc_hard_declension: 'Type II (Masc)',
  neut_o_declension: 'Type III (Neut -о)',
};

// Infer stem/ending from word and gender
const inferStemEnding = (word: string, gender?: string, stem?: string): { stem: string; ending: string } => {
  if (stem) {
    return { stem, ending: word.slice(stem.length) };
  }
  
  const w = word.toLowerCase();
  
  // Feminine -а/-я endings
  if (gender === 'f' && (w.endsWith('а') || w.endsWith('я'))) {
    return { stem: word.slice(0, -1), ending: word.slice(-1) };
  }
  
  // Neuter -о/-е endings
  if (gender === 'n' && (w.endsWith('о') || w.endsWith('е'))) {
    return { stem: word.slice(0, -1), ending: word.slice(-1) };
  }
  
  // Masculine - consonant ending (no visible ending)
  if (gender === 'm' && !w.endsWith('а') && !w.endsWith('я') && !w.endsWith('ь')) {
    return { stem: word, ending: '' };
  }
  
  // Default - try to find a vowel ending
  if (/[аяоеуюыиь]$/.test(w)) {
    return { stem: word.slice(0, -1), ending: word.slice(-1) };
  }
  
  return { stem: word, ending: '' };
};

interface WordIntroProps {
  words: VocabWord[];
  onComplete: () => void;
}

// Simple icon mapping for vocabulary categories
const WORD_ICONS: Record<string, string> = {
  // Family
  'мама': '👩',
  'папа': '👨',
  'брат': '👦',
  'сестра': '👧',
  // Animals
  'кот': '🐱',
  'собака': '🐕',
  // Places
  'дом': '🏠',
  'парк': '🌳',
  'метро': '🚇',
  'банк': '🏦',
  'ресторан': '🍽️',
  // Objects
  'книга': '📖',
  'телефон': '📱',
  'машина': '🚗',
  'окно': '🪟',
  'карта': '🗺️',
  // Food/Drink
  'кофе': '☕',
  'чай': '🍵',
  'вода': '💧',
  'хлеб': '🍞',
  'пицца': '🍕',
  // Transport
  'такси': '🚕',
  // Abstract
  'да': '✅',
  'нет': '❌',
  // Default
  'default': '📝',
};

const getWordIcon = (word: string): string => {
  const lowered = word.toLowerCase();
  return WORD_ICONS[lowered] || WORD_ICONS['default'];
};

export const WordIntro: React.FC<WordIntroProps> = ({ words, onComplete }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [seenWords, setSeenWords] = useState<Set<number>>(new Set([0]));

  const currentWord = words[currentIndex];
  const progress = (seenWords.size / words.length) * 100;
  const isLastWord = currentIndex === words.length - 1;
  const allSeen = seenWords.size === words.length;

  // Compute stem/ending breakdown
  const morphBreakdown = useMemo(() => {
    if (!currentWord) return null;
    return inferStemEnding(currentWord.word, currentWord.gender, currentWord.stem);
  }, [currentWord]);

  const handleNext = useCallback(() => {
    if (isLastWord && allSeen) {
      onComplete();
    } else {
      const nextIndex = (currentIndex + 1) % words.length;
      setCurrentIndex(nextIndex);
      setSeenWords(prev => new Set([...prev, nextIndex]));
    }
  }, [currentIndex, words.length, isLastWord, allSeen, onComplete]);

  const playAudio = useCallback(() => {
    if (currentWord.audio) {
      const audio = new Audio(`/audio/${currentWord.audio}`);
      audio.play().catch(() => {});
    }
  }, [currentWord.audio]);

  if (!currentWord) return null;

  return (
    <div className="flex flex-col h-full max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Lightbulb className="text-yellow-500" size={20} />
          <span className="font-bold text-gray-700">New Words</span>
        </div>
        <span className="text-gray-400 font-mono">
          {seenWords.size} / {words.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full mb-8 overflow-hidden">
        <motion.div
          className="h-full bg-yellow-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Word Card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="flex-1 flex flex-col"
        >
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-32 h-32 bg-gradient-to-br from-blue-50 to-indigo-100 rounded-3xl flex items-center justify-center shadow-lg">
              <span className="text-6xl">
                {currentWord.icon || getWordIcon(currentWord.word)}
              </span>
            </div>
          </div>

          {/* Russian Word with Morphological Breakdown */}
          <div className="text-center mb-2">
            {morphBreakdown && (morphBreakdown.ending || currentWord.gender) ? (
              <h2 className="text-4xl font-bold mb-1">
                <span className="text-gray-600">{morphBreakdown.stem}</span>
                {morphBreakdown.ending && (
                  <span className={clsx(
                    currentWord.gender === 'm' && 'text-blue-600',
                    currentWord.gender === 'f' && 'text-pink-600',
                    currentWord.gender === 'n' && 'text-purple-600',
                    !currentWord.gender && 'text-primary-600'
                  )}>
                    {morphBreakdown.ending}
                  </span>
                )}
                {!morphBreakdown.ending && currentWord.gender === 'm' && (
                  <span className="text-blue-400 text-2xl align-baseline">∅</span>
                )}
              </h2>
            ) : (
              <h2 className="text-4xl font-bold text-gray-900 mb-1">
                {currentWord.word}
              </h2>
            )}
            {currentWord.transliteration && (
              <p className="text-lg text-gray-400 italic">
                ({currentWord.transliteration})
              </p>
            )}
          </div>

          {/* Divider */}
          <div className="flex items-center justify-center my-4">
            <div className="h-px bg-gray-200 w-16" />
            <ChevronRight className="text-gray-300 mx-2" size={20} />
            <div className="h-px bg-gray-200 w-16" />
          </div>

          {/* Translation */}
          <div className="text-center mb-4">
            <p className="text-2xl text-primary-600 font-medium">
              {currentWord.translation}
            </p>
          </div>

          {/* Gender & Pattern Badges */}
          {(currentWord.gender || currentWord.pattern) && (
            <div className="flex items-center justify-center gap-2 mb-6">
              {currentWord.gender && (
                <span className={clsx(
                  "px-3 py-1 rounded-full text-xs font-bold",
                  currentWord.gender === 'm' && "bg-blue-100 text-blue-700",
                  currentWord.gender === 'f' && "bg-pink-100 text-pink-700",
                  currentWord.gender === 'n' && "bg-purple-100 text-purple-700",
                )}>
                  {currentWord.gender === 'm' ? 'Masculine' : currentWord.gender === 'f' ? 'Feminine' : 'Neuter'}
                </span>
              )}
              {currentWord.pattern && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-700 flex items-center gap-1">
                  <BookOpen size={12} />
                  {PATTERN_NAMES[currentWord.pattern] || currentWord.pattern.replace(/_/g, ' ')}
                </span>
              )}
            </div>
          )}

          {/* Audio Button */}
          {currentWord.audio && (
            <button
              onClick={playAudio}
              className="mx-auto mb-6 flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-600 transition-colors"
            >
              <Volume2 size={18} />
              <span className="font-medium">Play Audio</span>
            </button>
          )}

          {/* Hint */}
          {currentWord.hints && currentWord.hints.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <Lightbulb className="text-yellow-500 flex-shrink-0 mt-0.5" size={18} />
                <p className="text-yellow-800 text-sm">
                  {currentWord.hints[0]}
                </p>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation Dots */}
      <div className="flex justify-center gap-2 mb-6">
        {words.map((_, idx) => (
          <button
            key={idx}
            onClick={() => {
              setCurrentIndex(idx);
              setSeenWords(prev => new Set([...prev, idx]));
            }}
            className={clsx(
              "w-2.5 h-2.5 rounded-full transition-all",
              idx === currentIndex
                ? "bg-primary-500 w-6"
                : seenWords.has(idx)
                ? "bg-green-400"
                : "bg-gray-300"
            )}
          />
        ))}
      </div>

      {/* Action Button */}
      <button
        onClick={handleNext}
        className={clsx(
          "w-full py-4 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2",
          allSeen && isLastWord
            ? "bg-green-500 hover:bg-green-600 text-white"
            : "bg-primary-500 hover:bg-primary-600 text-white"
        )}
      >
        {allSeen && isLastWord ? (
          <>
            <Check size={20} />
            Start Practice
          </>
        ) : (
          <>
            Got it
            <ChevronRight size={20} />
          </>
        )}
      </button>
    </div>
  );
};

export default WordIntro;
