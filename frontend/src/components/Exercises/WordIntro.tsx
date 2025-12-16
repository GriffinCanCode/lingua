import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2, ChevronRight, Lightbulb, Check } from 'lucide-react';
import clsx from 'clsx';

export interface VocabWord {
  word: string;
  translation: string;
  transliteration?: string;
  audio?: string;
  hints?: string[];
  icon?: string;
  gender?: string;
}

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

          {/* Russian Word */}
          <div className="text-center mb-2">
            <h2 className="text-4xl font-bold text-gray-900 mb-1">
              {currentWord.word}
            </h2>
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
          <div className="text-center mb-6">
            <p className="text-2xl text-primary-600 font-medium">
              {currentWord.translation}
            </p>
            {currentWord.gender && (
              <span className={clsx(
                "inline-block mt-2 px-3 py-1 rounded-full text-xs font-bold",
                currentWord.gender === 'm' && "bg-blue-100 text-blue-700",
                currentWord.gender === 'f' && "bg-pink-100 text-pink-700",
                currentWord.gender === 'n' && "bg-gray-100 text-gray-700",
              )}>
                {currentWord.gender === 'm' ? 'Masculine' : currentWord.gender === 'f' ? 'Feminine' : 'Neuter'}
              </span>
            )}
          </div>

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
