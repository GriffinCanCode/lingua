import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, HelpCircle, ThumbsUp, RefreshCw, Info } from 'lucide-react';
import { srsService, ReviewItem, ReviewResult } from '../../services/srs';
import { useComponentLogger, useActionLogger, useTracedAsync } from '../../lib/logger';
import clsx from 'clsx';

export const SRSReview: React.FC = () => {
  const { logger, logAction } = useComponentLogger('SRSReview');
  const trackAction = useActionLogger('srs');
  const traceAsync = useTracedAsync('srs');

  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [results, setResults] = useState<ReviewResult[]>([]);

  useEffect(() => {
    loadReviews();
  }, []);

  const loadReviews = async () => {
    setLoading(true);
    try {
      const data = await traceAsync('loadDueReviews', () => srsService.getDueReviews());
      setReviews(data);
      logger.info('Reviews loaded', { count: data.length });
    } catch (err) {
      logger.error('Failed to load reviews', err instanceof Error ? err : undefined);
      // Mock data for UI development if backend is down
      // setReviews([{ sentence: { id: 1, text: 'Hello World', translation: 'Hola Mundo' }, patterns: [] }]);
    } finally {
      setLoading(false);
    }
  };

  const handleRating = (quality: number) => {
    const currentItem = reviews[currentIndex];
    logAction('review_rated', { quality, sentenceId: currentItem.sentence.id });

    const newResults = currentItem.patterns.map(p => ({
      pattern_id: p.id,
      quality,
    }));

    setResults(prev => [...prev, ...newResults]);

    if (currentIndex < reviews.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setShowAnswer(false);
    } else {
      setCompleted(true);
      submitResults([...results, ...newResults]);
    }
  };

  const submitResults = async (finalResults: ReviewResult[]) => {
    try {
      await traceAsync('submitReviews', () => srsService.submitReview(finalResults));
      trackAction('session_completed', { reviewCount: reviews.length, patterns: finalResults.length });
    } catch (err) {
      logger.error('Failed to submit reviews', err instanceof Error ? err : undefined);
    }
  };

  const handleNewSession = () => {
    trackAction('new_session_started');
    setCompleted(false);
    setCurrentIndex(0);
    setResults([]);
    loadReviews();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (completed) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto mt-12 text-center"
      >
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check size={40} strokeWidth={3} />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">Session Complete!</h2>
          <p className="text-gray-500 mb-8 text-lg">You've reviewed {reviews.length} sentences today.</p>
          <button
            onClick={handleNewSession}
            className="w-full bg-primary-600 text-white font-bold py-4 px-6 rounded-xl hover:bg-primary-700 transition-transform transform hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-primary-200"
          >
            Start New Session
          </button>
        </div>
      </motion.div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="max-w-md mx-auto mt-12 text-center">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mx-auto mb-6">
            <RefreshCw size={40} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Reviews Due</h2>
          <p className="text-gray-500 mb-8">You're all caught up! Check back later.</p>
          <button
            onClick={handleNewSession}
            className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800 transition-colors"
          >
            Review Anyway
          </button>
        </div>
      </div>
    );
  }

  const currentItem = reviews[currentIndex];
  const progress = ((currentIndex) / reviews.length) * 100;

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col">
      {/* Progress Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-green-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <span className="font-bold text-gray-400 font-mono">
          {currentIndex + 1} / {reviews.length}
        </span>
      </div>

      {/* Card Area */}
      <div className="flex-1 flex flex-col justify-center max-w-2xl mx-auto w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentItem.sentence.id}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="bg-white rounded-3xl shadow-xl border-b-4 border-gray-200 overflow-hidden min-h-[400px] flex flex-col"
          >
            {/* Question Side */}
            <div className="flex-1 p-10 flex flex-col items-center justify-center text-center">
              <h3 className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-6">Translate this sentence</h3>
              <p className="text-3xl md:text-4xl font-medium text-gray-800 leading-relaxed">
                {currentItem.sentence.text}
              </p>
            </div>

            {/* Answer Interaction Area */}
            <div className={clsx(
              "p-6 transition-colors duration-300",
              showAnswer ? "bg-gray-50" : "bg-white"
            )}>
              {!showAnswer ? (
                <button
                  onClick={() => setShowAnswer(true)}
                  className="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-4 rounded-xl text-lg shadow-lg shadow-green-200 transition-all transform hover:translate-y-[-2px]"
                >
                  Show Answer
                </button>
              ) : (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                  <div className="mb-8 text-center">
                    <p className="text-xl text-gray-700 font-medium mb-4">{currentItem.sentence.translation}</p>

                    {currentItem.patterns.length > 0 && (
                      <div className="inline-flex flex-wrap justify-center gap-2">
                        {currentItem.patterns.map(p => (
                          <span key={p.id} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700">
                            <Info size={12} className="mr-1" />
                            {p.description || p.pattern_type}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-4 gap-3">
                    <RatingButton
                      label="Again"
                      subLabel="< 1m"
                      color="red"
                      icon={X}
                      onClick={() => handleRating(0)}
                    />
                    <RatingButton
                      label="Hard"
                      subLabel="2d"
                      color="orange"
                      icon={HelpCircle}
                      onClick={() => handleRating(3)}
                    />
                    <RatingButton
                      label="Good"
                      subLabel="5d"
                      color="blue"
                      icon={ThumbsUp}
                      onClick={() => handleRating(4)}
                    />
                    <RatingButton
                      label="Easy"
                      subLabel="10d"
                      color="green"
                      icon={Check}
                      onClick={() => handleRating(5)}
                    />
                  </div>
                </div>
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
        "flex flex-col items-center justify-center p-3 rounded-xl border-b-4 active:border-b-0 active:translate-y-1 transition-all h-24",
        colorStyles[color]
      )}
    >
      <Icon size={24} className="mb-1" />
      <span className="font-bold text-sm">{label}</span>
      <span className="text-xs opacity-75">{subLabel}</span>
    </button>
  );
};
