import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, Trophy } from 'lucide-react';
import { getLesson, completeLesson, Lesson } from '../../services/curriculum';
import { LessonIntro } from './LessonIntro';
import { useComponentLogger } from '../../lib/logger';
import clsx from 'clsx';

export const LessonSession: React.FC = () => {
  const { nodeId } = useParams<{ nodeId: string }>();
  const navigate = useNavigate();
  const { logger } = useComponentLogger('LessonSession');

  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    if (nodeId) {
      loadLesson(nodeId);
    }
  }, [nodeId]);

  const loadLesson = async (id: string) => {
    setLoading(true);
    try {
      const data = await getLesson(id);
      setLesson(data);
      logger.info('Lesson loaded', { nodeId: id, sentenceCount: data.sentences.length });
    } catch (err) {
      logger.error('Failed to load lesson', err instanceof Error ? err : undefined);
    } finally {
      setLoading(false);
    }
  };

  const handleResult = (isCorrect: boolean) => {
    if (isCorrect) setCorrectCount(prev => prev + 1);

    if (lesson && currentIndex < lesson.sentences.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setShowAnswer(false);
    } else {
      finishLesson(isCorrect ? correctCount + 1 : correctCount);
    }
  };

  const finishLesson = async (finalCorrect: number) => {
    if (!lesson || !nodeId) return;

    setCompleted(true);
    try {
      await completeLesson(nodeId, finalCorrect, lesson.sentences.length);
      logger.info('Lesson completed', { correct: finalCorrect, total: lesson.sentences.length });
    } catch (err) {
      logger.error('Failed to submit lesson results', err instanceof Error ? err : undefined);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="text-center mt-12">
        <h2 className="text-2xl font-bold text-gray-900">Lesson not found</h2>
        <button onClick={() => navigate('/')} className="mt-4 text-primary-600 hover:underline">
          Return Home
        </button>
      </div>
    );
  }

  // Handle empty lessons (no sentences yet)
  if (lesson.sentences.length === 0) {
    return (
      <div className="text-center mt-12 max-w-md mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">📚</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{lesson.node_title}</h2>
          <p className="text-gray-500 mb-6">
            This lesson is being prepared. Check back soon for exercises!
          </p>
          <button 
            onClick={() => navigate('/')} 
            className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800 transition-colors"
          >
            Return to Path
          </button>
        </div>
      </div>
    );
  }

  // Introduction Screen
  if (showIntro) {
    return (
      <LessonIntro
        title={lesson.node_title}
        description={`Ready to master new concepts? This lesson contains ${lesson.sentences.length} exercises.`}
        content={lesson.extra_data?.content || {}}
        vocabulary={lesson.extra_data?.vocabulary || []}
        onStart={() => setShowIntro(false)}
      />
    );
  }

  // Completion Screen
  if (completed) {
    const percentage = Math.round((correctCount / lesson.sentences.length) * 100);

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md mx-auto mt-12 text-center"
      >
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-24 h-24 bg-yellow-100 text-yellow-600 rounded-full flex items-center justify-center mx-auto mb-6 relative">
            <Trophy size={48} />
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.5 }}
              className="absolute -right-2 -bottom-2 w-10 h-10 bg-green-500 rounded-full border-4 border-white flex items-center justify-center text-white font-bold text-sm"
            >
              +{correctCount * 10}
            </motion.div>
          </div>

          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">Lesson Complete!</h2>
          <div className="text-5xl font-black text-primary-600 mb-2">{percentage}%</div>
          <p className="text-gray-500 mb-8">
            You got {correctCount} out of {lesson.sentences.length} correct.
          </p>

          <div className="space-y-3">
            <button
              onClick={() => navigate('/')}
              className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800 transition-transform transform hover:scale-[1.02]"
            >
              Continue Path
            </button>
            <button
              onClick={() => {
                setCompleted(false);
                setCurrentIndex(0);
                setCorrectCount(0);
                setShowIntro(true);
              }}
              className="w-full bg-white text-gray-700 font-bold py-4 px-6 rounded-xl hover:bg-gray-50 border-2 border-gray-200 transition-colors"
            >
              Review Again
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  const currentSentence = lesson.sentences[currentIndex];
  const progress = ((currentIndex) / lesson.sentences.length) * 100;

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors">
          <X size={24} />
        </button>
        <div className="flex-1 mx-8 h-4 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <div className="font-mono text-gray-400 font-bold">
          {currentIndex + 1} / {lesson.sentences.length}
        </div>
      </div>

      {/* Card Area */}
      <div className="flex-1 flex flex-col justify-center max-w-2xl mx-auto w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentSentence.sentence_id}
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
                {currentSentence.text}
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
                  className="w-full bg-primary-600 hover:bg-primary-700 text-white font-bold py-4 rounded-xl text-lg shadow-lg shadow-primary-200 transition-all transform hover:translate-y-[-2px]"
                >
                  Show Answer
                </button>
              ) : (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                  <div className="mb-8 text-center">
                    <p className="text-xl text-gray-700 font-medium mb-2">{currentSentence.translation}</p>
                    <div className="flex justify-center gap-2 mt-4">
                      {currentSentence.patterns.map((p, i) => (
                        <span key={i} className="text-xs font-bold px-2 py-1 bg-blue-100 text-blue-700 rounded-md">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => handleResult(false)}
                      className="flex flex-col items-center justify-center p-4 rounded-xl border-b-4 border-red-200 bg-red-50 text-red-600 hover:bg-red-100 active:border-b-0 active:translate-y-1 transition-all"
                    >
                      <X size={24} className="mb-1" />
                      <span className="font-bold">Incorrect</span>
                    </button>
                    <button
                      onClick={() => handleResult(true)}
                      className="flex flex-col items-center justify-center p-4 rounded-xl border-b-4 border-green-200 bg-green-50 text-green-600 hover:bg-green-100 active:border-b-0 active:translate-y-1 transition-all"
                    >
                      <Check size={24} className="mb-1" />
                      <span className="font-bold">Correct</span>
                    </button>
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
