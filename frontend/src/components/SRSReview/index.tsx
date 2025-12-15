import React, { useState, useEffect } from 'react';
import { srsService, ReviewItem, ReviewResult } from '../../services/srs';
import { Check, X, HelpCircle, ThumbsUp } from 'lucide-react';

export const SRSReview: React.FC = () => {
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
      const data = await srsService.getDueReviews();
      setReviews(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRating = (quality: number) => {
    const currentItem = reviews[currentIndex];
    
    // Record result for each pattern in the sentence
    const newResults = currentItem.patterns.map(p => ({
      pattern_id: p.id,
      quality: quality
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
      await srsService.submitReview(finalResults);
    } catch (err) {
      console.error("Failed to submit reviews", err);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center bg-white rounded-lg shadow mt-8">
        <h2 className="text-2xl font-bold mb-4 text-green-600">Session Complete!</h2>
        <p className="text-gray-600 mb-6">You've reviewed {reviews.length} sentences.</p>
        <button
          onClick={() => {
            setCompleted(false);
            setCurrentIndex(0);
            setResults([]);
            loadReviews();
          }}
          className="bg-primary-600 text-white px-6 py-2 rounded hover:bg-primary-700"
        >
          Start New Session
        </button>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center bg-white rounded-lg shadow mt-8">
        <h2 className="text-2xl font-bold mb-4">No Reviews Due</h2>
        <p className="text-gray-600 mb-6">You're all caught up! Check back later or add new content.</p>
      </div>
    );
  }

  const currentItem = reviews[currentIndex];

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Sentence Review</h2>
        <div className="text-sm text-gray-500">
          {currentIndex + 1} / {reviews.length}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden min-h-[400px] flex flex-col">
        {/* Progress bar */}
        <div className="w-full bg-gray-200 h-2">
          <div 
            className="bg-primary-600 h-2 transition-all duration-300" 
            style={{ width: `${((currentIndex) / reviews.length) * 100}%` }}
          ></div>
        </div>

        <div className="p-8 flex-1 flex flex-col items-center justify-center">
          <div className="text-3xl font-medium text-center mb-12">
            {currentItem.sentence.text}
          </div>

          {!showAnswer ? (
            <button
              onClick={() => setShowAnswer(true)}
              className="bg-primary-600 text-white px-8 py-3 rounded-full hover:bg-primary-700 transition shadow-md"
            >
              Show Translation
            </button>
          ) : (
            <div className="w-full animate-fadeIn">
              <div className="text-xl text-gray-600 text-center mb-8 border-t pt-8">
                {currentItem.sentence.translation}
              </div>

              {currentItem.patterns.length > 0 && (
                <div className="mb-8 bg-blue-50 p-4 rounded-lg">
                  <h4 className="text-sm font-bold text-blue-800 uppercase tracking-wide mb-2">Patterns in this sentence:</h4>
                  <ul className="space-y-1">
                    {currentItem.patterns.map(p => (
                      <li key={p.id} className="text-blue-700 text-sm flex items-start gap-2">
                        <span className="mt-1">•</span>
                        <span>{p.description || p.pattern_type}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-4 gap-4 mt-8">
                <button
                  onClick={() => handleRating(0)}
                  className="flex flex-col items-center p-4 rounded-lg hover:bg-red-50 border border-transparent hover:border-red-200 transition"
                >
                  <X className="mb-2 text-red-500" />
                  <span className="font-bold text-red-700">Again</span>
                  <span className="text-xs text-red-400 mt-1">&lt; 1 min</span>
                </button>
                <button
                  onClick={() => handleRating(3)}
                  className="flex flex-col items-center p-4 rounded-lg hover:bg-orange-50 border border-transparent hover:border-orange-200 transition"
                >
                  <HelpCircle className="mb-2 text-orange-500" />
                  <span className="font-bold text-orange-700">Hard</span>
                  <span className="text-xs text-orange-400 mt-1">~2 days</span>
                </button>
                <button
                  onClick={() => handleRating(4)}
                  className="flex flex-col items-center p-4 rounded-lg hover:bg-blue-50 border border-transparent hover:border-blue-200 transition"
                >
                  <ThumbsUp className="mb-2 text-blue-500" />
                  <span className="font-bold text-blue-700">Good</span>
                  <span className="text-xs text-blue-400 mt-1">~5 days</span>
                </button>
                <button
                  onClick={() => handleRating(5)}
                  className="flex flex-col items-center p-4 rounded-lg hover:bg-green-50 border border-transparent hover:border-green-200 transition"
                >
                  <Check className="mb-2 text-green-500" />
                  <span className="font-bold text-green-700">Easy</span>
                  <span className="text-xs text-green-400 mt-1">~10 days</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

