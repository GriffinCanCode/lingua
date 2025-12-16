import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, HelpCircle, ThumbsUp, Volume2, Eye, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';

interface VocabCard {
  id: string;
  word: string;
  translation: string;
  transliteration?: string;
  gender?: string;
  audio?: string;
  example?: { ru: string; en: string };
  lastReview?: string;
  dueDate?: string;
}

// Mock data - in production this would come from the API
const MOCK_VOCAB: VocabCard[] = [
  { id: '1', word: 'привет', translation: 'hello', transliteration: 'privyet', example: { ru: 'Привет! Как дела?', en: 'Hello! How are you?' } },
  { id: '2', word: 'спасибо', translation: 'thank you', transliteration: 'spasiba', example: { ru: 'Спасибо большое!', en: 'Thank you very much!' } },
  { id: '3', word: 'пожалуйста', translation: 'please / you\'re welcome', transliteration: 'pazhalusta' },
  { id: '4', word: 'да', translation: 'yes', transliteration: 'da' },
  { id: '5', word: 'нет', translation: 'no', transliteration: 'nyet' },
  { id: '6', word: 'хорошо', translation: 'good / okay', transliteration: 'kharasho', example: { ru: 'Всё хорошо.', en: 'Everything is good.' } },
  { id: '7', word: 'большой', translation: 'big', transliteration: "bol'shoy", gender: 'm' },
  { id: '8', word: 'маленький', translation: 'small', transliteration: "malen'kiy", gender: 'm' },
];

export const SRSReview: React.FC = () => {
  const navigate = useNavigate();
  const [cards, setCards] = useState<VocabCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [results, setResults] = useState<{ id: string; quality: number }[]>([]);
  const [sessionXp, setSessionXp] = useState(0);

  useEffect(() => {
    loadReviewCards();
  }, []);

  const loadReviewCards = async () => {
    setLoading(true);
    // TODO: Replace with actual API call
    // const data = await srsService.getDueVocab();
    await new Promise(r => setTimeout(r, 500)); // Simulate loading
    setCards(MOCK_VOCAB.slice(0, 5)); // Take 5 cards for review
    setLoading(false);
  };

  const handleRating = useCallback((quality: number) => {
    const currentCard = cards[currentIndex];
    const xpEarned = quality >= 4 ? 10 : quality >= 3 ? 5 : 2;
    setSessionXp(prev => prev + xpEarned);
    setResults(prev => [...prev, { id: currentCard.id, quality }]);

    if (currentIndex < cards.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setShowAnswer(false);
    } else {
      setCompleted(true);
    }
  }, [cards, currentIndex]);

  const handleNewSession = () => {
    setCompleted(false);
    setCurrentIndex(0);
    setResults([]);
    setSessionXp(0);
    setShowAnswer(false);
    loadReviewCards();
  };

  const playAudio = (audio?: string) => {
    if (audio) {
      const audioEl = new Audio(`/audio/${audio}`);
      audioEl.play().catch(() => {});
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (completed) {
    const correctCount = results.filter(r => r.quality >= 4).length;
    const accuracy = Math.round((correctCount / results.length) * 100);

    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-md mx-auto mt-12 text-center">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-24 h-24 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check size={48} strokeWidth={3} />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">Review Complete!</h2>
          <div className="flex justify-center gap-6 my-6">
            <div className="text-center">
              <p className="text-3xl font-black text-primary-600">{cards.length}</p>
              <p className="text-sm text-gray-500">Words</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-black text-green-600">{accuracy}%</p>
              <p className="text-sm text-gray-500">Accuracy</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-black text-yellow-600">+{sessionXp}</p>
              <p className="text-sm text-gray-500">XP</p>
            </div>
          </div>
          <div className="space-y-3">
            <button
              onClick={handleNewSession}
              className="w-full bg-primary-600 text-white font-bold py-4 px-6 rounded-xl hover:bg-primary-700 transition-all shadow-lg shadow-primary-200"
            >
              Review More Words
            </button>
            <button
              onClick={() => navigate('/')}
              className="w-full bg-gray-100 text-gray-700 font-bold py-4 px-6 rounded-xl hover:bg-gray-200 transition-colors"
            >
              Back to Learning
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="max-w-md mx-auto mt-12 text-center">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check size={40} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">All Caught Up!</h2>
          <p className="text-gray-500 mb-8">No words due for review. Keep learning to add more!</p>
          <button
            onClick={() => navigate('/')}
            className="w-full bg-primary-600 text-white font-bold py-4 px-6 rounded-xl hover:bg-primary-700 transition-colors"
          >
            Continue Learning
          </button>
        </div>
      </div>
    );
  }

  const currentCard = cards[currentIndex];
  const progress = (currentIndex / cards.length) * 100;

  return (
    <div className="max-w-2xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-gray-900">Vocabulary Review</h2>
          <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-bold flex items-center gap-1">
            <Zap size={14} /> +{sessionXp} XP
          </span>
        </div>
        <span className="font-mono text-gray-400">{currentIndex + 1} / {cards.length}</span>
      </div>

      {/* Progress Bar */}
      <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-8">
        <motion.div
          className="h-full bg-green-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Flashcard */}
      <div className="flex-1 flex flex-col justify-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentCard.id}
            initial={{ opacity: 0, rotateY: -90 }}
            animate={{ opacity: 1, rotateY: 0 }}
            exit={{ opacity: 0, rotateY: 90 }}
            transition={{ duration: 0.3 }}
            className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden"
          >
            {/* Question Side */}
            <div className="p-10 text-center min-h-[250px] flex flex-col items-center justify-center">
              <p className="text-5xl font-bold text-gray-900 mb-3">{currentCard.word}</p>
              {currentCard.transliteration && (
                <p className="text-lg text-gray-400 italic">({currentCard.transliteration})</p>
              )}
              {currentCard.gender && (
                <span className={clsx(
                  "mt-3 px-3 py-1 rounded-full text-xs font-bold",
                  currentCard.gender === 'm' && "bg-blue-100 text-blue-700",
                  currentCard.gender === 'f' && "bg-pink-100 text-pink-700",
                  currentCard.gender === 'n' && "bg-gray-100 text-gray-700",
                )}>
                  {currentCard.gender === 'm' ? 'Masculine' : currentCard.gender === 'f' ? 'Feminine' : 'Neuter'}
                </span>
              )}
              {currentCard.audio && (
                <button
                  onClick={() => playAudio(currentCard.audio)}
                  className="mt-4 p-3 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
                >
                  <Volume2 size={20} />
                </button>
              )}
            </div>

            {/* Answer Section */}
            <div className={clsx("p-6 transition-colors", showAnswer ? "bg-gray-50" : "bg-white")}>
              {!showAnswer ? (
                <button
                  onClick={() => setShowAnswer(true)}
                  className="w-full bg-primary-500 hover:bg-primary-600 text-white font-bold py-4 rounded-xl text-lg shadow-lg shadow-primary-200 transition-all flex items-center justify-center gap-2"
                >
                  <Eye size={20} /> Show Answer
                </button>
              ) : (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                  <div className="text-center py-4 border-b border-gray-200">
                    <p className="text-2xl font-bold text-primary-600">{currentCard.translation}</p>
                    {currentCard.example && (
                      <div className="mt-4 text-left bg-white p-4 rounded-xl border border-gray-100">
                        <p className="text-gray-800 font-medium">{currentCard.example.ru}</p>
                        <p className="text-gray-500 text-sm mt-1">{currentCard.example.en}</p>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-4 gap-3">
                    <RatingButton label="Again" subLabel="< 1m" color="red" icon={X} onClick={() => handleRating(1)} />
                    <RatingButton label="Hard" subLabel="2d" color="orange" icon={HelpCircle} onClick={() => handleRating(3)} />
                    <RatingButton label="Good" subLabel="5d" color="blue" icon={ThumbsUp} onClick={() => handleRating(4)} />
                    <RatingButton label="Easy" subLabel="10d" color="green" icon={Check} onClick={() => handleRating(5)} />
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

const RatingButton: React.FC<{
  label: string;
  subLabel: string;
  color: 'red' | 'orange' | 'blue' | 'green';
  icon: React.ElementType;
  onClick: () => void;
}> = ({ label, subLabel, color, icon: Icon, onClick }) => {
  const colorStyles = {
    red: "bg-red-50 text-red-600 hover:bg-red-100 border-red-200",
    orange: "bg-orange-50 text-orange-600 hover:bg-orange-100 border-orange-200",
    blue: "bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-200",
    green: "bg-green-50 text-green-600 hover:bg-green-100 border-green-200",
  };

  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex flex-col items-center justify-center p-3 rounded-xl border-b-4 active:border-b-0 active:translate-y-1 transition-all h-20",
        colorStyles[color]
      )}
    >
      <Icon size={20} className="mb-1" />
      <span className="font-bold text-xs">{label}</span>
      <span className="text-[10px] opacity-75">{subLabel}</span>
    </button>
  );
};
