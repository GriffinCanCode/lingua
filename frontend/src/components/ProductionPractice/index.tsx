import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, CheckCircle, XCircle, Lightbulb, ArrowRight, Keyboard, Volume2, Zap, Trophy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';

interface Challenge {
  id: string;
  type: 'translate' | 'fill_blank' | 'listen';
  prompt: string;
  answer: string;
  alternatives?: string[];
  hint?: string;
  difficulty: number;
}

// Mock challenges - in production these come from the API based on learned vocabulary
const MOCK_CHALLENGES: Challenge[] = [
  { id: '1', type: 'translate', prompt: 'Translate: "Hello, how are you?"', answer: 'привет, как дела?', alternatives: ['привет как дела', 'привет, как ты'], hint: 'Use the informal greeting', difficulty: 1 },
  { id: '2', type: 'translate', prompt: 'Translate: "Thank you very much"', answer: 'спасибо большое', alternatives: ['большое спасибо'], hint: 'Big thanks!', difficulty: 1 },
  { id: '3', type: 'translate', prompt: 'Translate: "I have a book"', answer: 'у меня есть книга', alternatives: ['у меня книга'], hint: 'Use the construction "У меня есть..."', difficulty: 2 },
  { id: '4', type: 'translate', prompt: 'Translate: "This is good"', answer: 'это хорошо', hint: 'Use "это" for "this is"', difficulty: 1 },
  { id: '5', type: 'translate', prompt: 'Translate: "Where is the metro?"', answer: 'где метро?', alternatives: ['где находится метро'], hint: 'Metro is the same word in Russian', difficulty: 2 },
];

// Levenshtein distance for fuzzy matching
function levenshtein(a: string, b: string): number {
  const matrix: number[][] = [];
  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      matrix[i][j] = b[i - 1] === a[j - 1]
        ? matrix[i - 1][j - 1]
        : Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1);
    }
  }
  return matrix[b.length][a.length];
}

function checkAnswer(input: string, answer: string, alternatives?: string[]): { correct: boolean; typo: boolean } {
  const normalizedInput = input.toLowerCase().trim().replace(/[.,!?]/g, '');
  const normalizedAnswer = answer.toLowerCase().trim().replace(/[.,!?]/g, '');

  if (normalizedInput === normalizedAnswer) return { correct: true, typo: false };

  // Check alternatives
  if (alternatives?.some(alt => normalizedInput === alt.toLowerCase().trim().replace(/[.,!?]/g, ''))) {
    return { correct: true, typo: false };
  }

  // Check for typo (within 2 character distance for short answers, 3 for longer)
  const threshold = normalizedAnswer.length > 10 ? 3 : 2;
  const distance = levenshtein(normalizedInput, normalizedAnswer);
  if (distance <= threshold) return { correct: true, typo: true };

  return { correct: false, typo: false };
}

export const ProductionPractice: React.FC = () => {
  const navigate = useNavigate();
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userInput, setUserInput] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{ correct: boolean; typo: boolean } | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [sessionXp, setSessionXp] = useState(0);

  useEffect(() => {
    loadChallenges();
  }, []);

  const loadChallenges = async () => {
    setLoading(true);
    await new Promise(r => setTimeout(r, 300));
    setChallenges(MOCK_CHALLENGES);
    setLoading(false);
  };

  const handleSubmit = useCallback((e?: React.FormEvent) => {
    e?.preventDefault();
    if (!userInput.trim() || submitted) return;

    const current = challenges[currentIndex];
    const checkResult = checkAnswer(userInput, current.answer, current.alternatives);
    setResult(checkResult);
    setSubmitted(true);

    if (checkResult.correct) {
      setScore(prev => ({ ...prev, correct: prev.correct + 1 }));
      setSessionXp(prev => prev + (checkResult.typo ? 5 : 10));
    }
  }, [userInput, submitted, challenges, currentIndex]);

  const handleNext = useCallback(() => {
    if (currentIndex < challenges.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setUserInput('');
      setSubmitted(false);
      setResult(null);
      setShowHint(false);
      setScore(prev => ({ ...prev, total: prev.total + 1 }));
    } else {
      setScore(prev => ({ ...prev, total: prev.total + 1 }));
      setCompleted(true);
    }
  }, [currentIndex, challenges.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (submitted) handleNext();
      else handleSubmit();
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
    const accuracy = Math.round((score.correct / score.total) * 100);
    return (
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="max-w-md mx-auto mt-12 text-center">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className={clsx(
            "w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6",
            accuracy >= 80 ? "bg-green-100 text-green-600" : accuracy >= 50 ? "bg-yellow-100 text-yellow-600" : "bg-red-100 text-red-600"
          )}>
            <Trophy size={48} />
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">Practice Complete!</h2>
          <div className="flex justify-center gap-6 my-6">
            <div className="text-center">
              <p className="text-3xl font-black text-primary-600">{score.correct}/{score.total}</p>
              <p className="text-sm text-gray-500">Correct</p>
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
              onClick={() => { setCompleted(false); setCurrentIndex(0); setScore({ correct: 0, total: 0 }); setSessionXp(0); setUserInput(''); setSubmitted(false); setResult(null); }}
              className="w-full bg-primary-600 text-white font-bold py-4 px-6 rounded-xl hover:bg-primary-700 shadow-lg shadow-primary-200"
            >
              Practice Again
            </button>
            <button onClick={() => navigate('/')} className="w-full bg-gray-100 text-gray-700 font-bold py-4 px-6 rounded-xl hover:bg-gray-200">
              Back to Learning
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  const current = challenges[currentIndex];
  const progress = (currentIndex / challenges.length) * 100;

  return (
    <div className="max-w-2xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold text-gray-900">Writing Practice</h2>
          <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-bold flex items-center gap-1">
            <Zap size={14} /> +{sessionXp} XP
          </span>
        </div>
        <span className="font-mono text-gray-400">{currentIndex + 1} / {challenges.length}</span>
      </div>

      {/* Progress */}
      <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-8">
        <motion.div className="h-full bg-primary-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${progress}%` }} />
      </div>

      {/* Challenge Card */}
      <div className="flex-1 flex flex-col justify-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden"
          >
            {/* Prompt */}
            <div className="p-8 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <span className="px-3 py-1 bg-primary-100 text-primary-700 text-xs font-bold uppercase rounded-full">
                  {current.type === 'translate' ? 'Translation' : current.type}
                </span>
                <div className="flex gap-1">
                  {[1, 2, 3].map(i => (
                    <div key={i} className={clsx("w-2 h-2 rounded-full", i <= current.difficulty ? "bg-primary-500" : "bg-gray-200")} />
                  ))}
                </div>
              </div>
              <p className="text-xl font-medium text-gray-800">{current.prompt}</p>
            </div>

            {/* Input Area */}
            <div className="p-8">
              {!submitted ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="relative">
                    <textarea
                      value={userInput}
                      onChange={(e) => setUserInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your answer in Russian..."
                      className="w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-primary-100 focus:border-primary-500 transition-all min-h-[120px] text-lg resize-none"
                      autoFocus
                    />
                    <div className="absolute bottom-3 right-3 flex items-center gap-2 text-gray-400">
                      <Keyboard size={16} />
                      <span className="text-xs">Enter to submit</span>
                    </div>
                  </div>

                  {/* Hint */}
                  <AnimatePresence>
                    {showHint && current.hint && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-yellow-50 p-4 rounded-xl border border-yellow-100"
                      >
                        <div className="flex items-start gap-3">
                          <Lightbulb size={18} className="text-yellow-500 mt-0.5" />
                          <p className="text-yellow-800 text-sm">{current.hint}</p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={() => setShowHint(true)}
                      disabled={showHint || !current.hint}
                      className="text-gray-500 hover:text-primary-600 disabled:opacity-30 font-medium flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-50"
                    >
                      <Lightbulb size={18} /> Hint
                    </button>
                    <button
                      type="submit"
                      disabled={!userInput.trim()}
                      className="bg-primary-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-primary-700 disabled:opacity-50 shadow-lg shadow-primary-200 flex items-center gap-2"
                    >
                      Check <Send size={18} />
                    </button>
                  </div>
                </form>
              ) : (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                  {/* Result */}
                  <div className={clsx(
                    "p-6 rounded-2xl flex items-start gap-4",
                    result?.correct ? "bg-green-50" : "bg-red-50"
                  )}>
                    {result?.correct ? (
                      <CheckCircle className="text-green-600 shrink-0 mt-1" size={28} />
                    ) : (
                      <XCircle className="text-red-600 shrink-0 mt-1" size={28} />
                    )}
                    <div className="flex-1">
                      <p className={clsx("font-bold text-xl mb-1", result?.correct ? "text-green-800" : "text-red-800")}>
                        {result?.correct ? (result.typo ? 'Almost! Watch the spelling.' : 'Correct!') : 'Not quite right'}
                      </p>
                      {!result?.correct && (
                        <div className="mt-2">
                          <p className="text-gray-600 text-sm">Correct answer:</p>
                          <p className="text-lg font-medium text-gray-900">{current.answer}</p>
                        </div>
                      )}
                      {result?.typo && (
                        <p className="text-green-700 text-sm mt-1">Your answer: {userInput}</p>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={handleNext}
                    className="w-full bg-gray-900 text-white font-bold py-4 rounded-xl hover:bg-gray-800 flex items-center justify-center gap-2"
                  >
                    {currentIndex < challenges.length - 1 ? 'Continue' : 'Finish'} <ArrowRight size={20} />
                  </button>
                </motion.div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};
