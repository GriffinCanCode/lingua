import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Heart, Trophy, Check, XCircle } from 'lucide-react';
import clsx from 'clsx';

import { getLessonExercises, completeLesson, LessonExercises } from '../../services/curriculum';
import { LessonIntro } from './LessonIntro';
import { useComponentLogger } from '../../lib/logger';
import { WordBank, Typing, Matching, MultipleChoice, FillBlank } from '../Exercises';
import type { Exercise, ExerciseResult, ValidationResult } from '../../types/exercises';

// Maximum hearts (lives) per lesson
const MAX_HEARTS = 3;

export const LessonSession: React.FC = () => {
  const { nodeId } = useParams<{ nodeId: string }>();
  const navigate = useNavigate();
  const { logger } = useComponentLogger('LessonSession');

  // State
  const [lesson, setLesson] = useState<LessonExercises | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hearts, setHearts] = useState(MAX_HEARTS);
  const [results, setResults] = useState<ExerciseResult[]>([]);
  const [showFeedback, setShowFeedback] = useState<ValidationResult | null>(null);
  const [showIntro, setShowIntro] = useState(true);
  const [completed, setCompleted] = useState(false);

  // Load lesson exercises
  useEffect(() => {
    if (!nodeId) return;

    const loadExercises = async () => {
      setLoading(true);
      try {
        const data = await getLessonExercises(nodeId);
        setLesson(data);
        logger.info('Exercises loaded', { nodeId, count: data.exercises.length });
      } catch (err) {
        logger.error('Failed to load exercises', err instanceof Error ? err : undefined);
      } finally {
        setLoading(false);
      }
    };

    loadExercises();
  }, [nodeId, logger]);

  // Current exercise
  const currentExercise = useMemo(() =>
    lesson?.exercises[currentIndex] ?? null,
    [lesson, currentIndex]
  );

  // Progress percentage
  const progress = useMemo(() =>
    lesson ? (currentIndex / lesson.exercises.length) * 100 : 0,
    [lesson, currentIndex]
  );

  // Correct count
  const correctCount = useMemo(() =>
    results.filter(r => r.correct).length,
    [results]
  );

  // Validate answer
  const validateAnswer = useCallback((answer: string | string[], exercise: Exercise): ValidationResult => {
    const normalize = (s: string) => s.toLowerCase().trim().replace(/[.,!?;:]/g, '');

    switch (exercise.type) {
      case 'word_bank':
        return {
          correct: normalize(answer as string) === normalize(exercise.targetText),
          correctAnswer: exercise.targetText,
        };

      case 'typing': {
        const normalizedAnswer = normalize(answer as string);
        const isCorrect = exercise.acceptableAnswers.some(
          acc => normalize(acc) === normalizedAnswer
        ) || normalize(exercise.targetText) === normalizedAnswer;

        // Check for close typo
        const typoDetected = !isCorrect && levenshtein(normalizedAnswer, normalize(exercise.targetText)) <= 2;

        return {
          correct: isCorrect || typoDetected,
          correctAnswer: exercise.targetText,
          typoDetected,
          feedback: typoDetected ? 'Almost! Watch your spelling.' : undefined,
        };
      }

      case 'multiple_choice':
        return {
          correct: answer === exercise.correctAnswer,
          correctAnswer: exercise.correctAnswer,
        };

      case 'fill_blank':
        return {
          correct: answer === exercise.correctAnswer,
          correctAnswer: exercise.correctAnswer,
        };

      case 'matching':
        // Matching auto-submits when all pairs matched
        return { correct: true, correctAnswer: '' };

      default:
        return { correct: false, correctAnswer: '' };
    }
  }, []);

  // Finish lesson
  const finishLesson = useCallback(async () => {
    if (!lesson || !nodeId) return;
    setCompleted(true);
    const correct = results.filter(r => r.correct).length + (showFeedback?.correct ? 1 : 0);
    try {
      await completeLesson(nodeId, correct, lesson.exercises.length);
      logger.info('Lesson completed', { correct, total: lesson.exercises.length });
    } catch (err) {
      logger.error('Failed to submit results', err instanceof Error ? err : undefined);
    }
  }, [lesson, nodeId, results, showFeedback, logger]);

  // Handle answer submission
  const handleSubmit = useCallback((answer: string | string[]) => {
    if (!currentExercise) return;

    const validation = validateAnswer(answer, currentExercise);
    setShowFeedback(validation);

    const result: ExerciseResult = {
      exerciseId: currentExercise.id,
      correct: validation.correct,
      userAnswer: answer,
      timeSpentMs: 0,
      attempts: 1,
    };
    setResults(prev => [...prev, result]);

    if (!validation.correct) setHearts(prev => prev - 1);

    setTimeout(() => {
      setShowFeedback(null);
      if (hearts <= 1 && !validation.correct) {
        setCompleted(true);
      } else if (lesson && currentIndex < lesson.exercises.length - 1) {
        setCurrentIndex(prev => prev + 1);
      } else {
        finishLesson();
      }
    }, validation.correct ? 800 : 1500);
  }, [currentExercise, validateAnswer, hearts, lesson, currentIndex, finishLesson]);

  // Render exercise component
  const renderExercise = useCallback((exercise: Exercise) => {
    const props = {
      exercise,
      onSubmit: handleSubmit,
      disabled: !!showFeedback,
    };

    switch (exercise.type) {
      case 'word_bank':
        return <WordBank {...props} exercise={exercise} />;
      case 'typing':
        return <Typing {...props} exercise={exercise} />;
      case 'matching':
        return <Matching {...props} exercise={exercise} />;
      case 'multiple_choice':
        return <MultipleChoice {...props} exercise={exercise} />;
      case 'fill_blank':
        return <FillBlank {...props} exercise={exercise} />;
      default:
        return <div>Unknown exercise type</div>;
    }
  }, [handleSubmit, showFeedback]);

  // Loading state
  if (loading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  // Not found
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

  // Empty lesson
  if (lesson.exercises.length === 0) {
    return (
      <div className="text-center mt-12 max-w-md mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">📚</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{lesson.node_title}</h2>
          <p className="text-gray-500 mb-6">This lesson is being prepared. Check back soon!</p>
          <button onClick={() => navigate('/')} className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800">
            Return to Path
          </button>
        </div>
      </div>
    );
  }

  // Brief intro screen before exercises
  if (showIntro) {
    return (
      <LessonIntro
        title={lesson.node_title}
        description={`${lesson.total_exercises} exercises to complete`}
        content={lesson.content || {}}
        vocabulary={lesson.vocabulary}
        onStart={() => setShowIntro(false)}
      />
    );
  }

  // Completion screen
  if (completed) {
    const percentage = Math.round((correctCount / lesson.exercises.length) * 100);
    const passed = hearts > 0;

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md mx-auto mt-12 text-center"
      >
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className={clsx(
            "w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6",
            passed ? "bg-yellow-100 text-yellow-600" : "bg-red-100 text-red-600"
          )}>
            {passed ? <Trophy size={48} /> : <XCircle size={48} />}
          </div>

          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">
            {passed ? 'Lesson Complete!' : 'Out of Hearts'}
          </h2>
          <div className={clsx(
            "text-5xl font-black mb-2",
            passed ? "text-primary-600" : "text-red-500"
          )}>
            {percentage}%
          </div>
          <p className="text-gray-500 mb-8">
            {correctCount} of {lesson.exercises.length} correct
          </p>

          <div className="space-y-3">
            <button
              onClick={() => navigate('/')}
              className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800"
            >
              Continue
            </button>
            <button
              onClick={() => {
                setCompleted(false);
                setCurrentIndex(0);
                setHearts(MAX_HEARTS);
                setResults([]);
                setShowIntro(true);
              }}
              className="w-full bg-white text-gray-700 font-bold py-4 px-6 rounded-xl hover:bg-gray-50 border-2 border-gray-200"
            >
              Try Again
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  // Active lesson
  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pt-4">
        <button
          onClick={() => navigate('/')}
          className="p-2 hover:bg-gray-100 rounded-lg text-gray-500"
        >
          <X size={24} />
        </button>

        {/* Progress bar */}
        <div className="flex-1 mx-4 h-4 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Hearts */}
        <div className="flex items-center gap-1">
          {Array.from({ length: MAX_HEARTS }).map((_, i) => (
            <Heart
              key={i}
              size={20}
              className={clsx(
                "transition-colors",
                i < hearts ? "fill-red-500 text-red-500" : "text-gray-300"
              )}
            />
          ))}
        </div>

        {/* Counter */}
        <div className="ml-4 font-mono text-gray-400 font-bold">
          {currentIndex + 1}/{lesson.exercises.length}
        </div>
      </div>

      {/* Exercise Area */}
      <div className="flex-1 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentExercise?.id}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="flex-1 bg-white rounded-3xl shadow-xl border border-gray-100 p-8 flex flex-col"
          >
            {currentExercise && renderExercise(currentExercise)}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Feedback overlay */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className={clsx(
              "fixed bottom-0 left-0 right-0 p-6 flex items-center gap-4",
              showFeedback.correct ? "bg-green-100" : "bg-red-100"
            )}
          >
            <div className={clsx(
              "w-12 h-12 rounded-full flex items-center justify-center",
              showFeedback.correct ? "bg-green-500" : "bg-red-500"
            )}>
              {showFeedback.correct
                ? <Check className="text-white" size={24} />
                : <X className="text-white" size={24} />
              }
            </div>
            <div className="flex-1">
              <p className={clsx(
                "font-bold text-lg",
                showFeedback.correct ? "text-green-700" : "text-red-700"
              )}>
                {showFeedback.correct
                  ? (showFeedback.typoDetected ? 'Almost correct!' : 'Correct!')
                  : 'Incorrect'}
              </p>
              {!showFeedback.correct && (
                <p className="text-red-600">
                  Correct answer: <strong>{showFeedback.correctAnswer}</strong>
                </p>
              )}
              {showFeedback.feedback && (
                <p className="text-gray-600 text-sm">{showFeedback.feedback}</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Levenshtein distance helper
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

export default LessonSession;
