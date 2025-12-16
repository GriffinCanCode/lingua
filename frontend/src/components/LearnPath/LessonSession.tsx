import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronRight, ChevronLeft } from 'lucide-react';
import clsx from 'clsx';

import { getLessonExercises, completeLesson, LessonExercises } from '../../services/curriculum';
import { getGrammarConfig, GrammarConfig } from '../../services/languages';
import { LessonIntro } from './LessonIntro';
import { TeachingCard } from '../Teaching';
import { useComponentLogger } from '../../lib/logger';
import { microcopy } from '../../lib/microcopy';
import {
  Confetti, SuccessBurst, XPGain, Heart, Crown, ProgressRing, Mascot,
} from '../Celebrations';
import {
  WordBank, Typing, Matching, MultipleChoice, FillBlank,
  PatternFill, PatternApply, ParadigmComplete, DialogueTranslate,
} from '../Exercises';
import type { Exercise, ExerciseResult, ValidationResult } from '../../types/exercises';
import type { TeachingContent, ModuleType } from '../../types/teaching';

const MAX_HEARTS = 3;
const XP_PER_EXERCISE = 5;
const XP_BONUS_STREAK = 2;
const XP_PERFECT_BONUS = 10;

type ModulePhase = 'teaching' | 'exercises' | 'complete';

interface ModuleData {
  id: string;
  title: string;
  type: ModuleType;
  teaching: TeachingContent[];
  exercises: Exercise[];
}

// Feedback panel with personality
const FeedbackPanel: React.FC<{
  validation: ValidationResult;
  streak: number;
  onContinue?: () => void;
}> = ({ validation, streak }) => {
  const message = useMemo(() => {
    if (validation.correct) {
      if (validation.typoDetected) return microcopy.typo();
      return microcopy.success(streak);
    }
    return microcopy.error();
  }, [validation, streak]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 100 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 100 }}
      className={clsx(
        "fixed bottom-0 left-0 right-0 p-6 flex items-center gap-4 z-30",
        validation.correct ? "bg-green-100" : "bg-red-100"
      )}
    >
      <div className={clsx(
        "w-14 h-14 rounded-full flex items-center justify-center shrink-0",
        validation.correct ? "bg-green-500" : "bg-red-500"
      )}>
        {validation.correct ? (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
          </svg>
        ) : (
          <X className="text-white" size={28} />
        )}
      </div>
      
      <div className="flex-1">
        <p className={clsx(
          "font-black text-xl",
          validation.correct ? "text-green-700" : "text-red-700"
        )}>
          {message}
        </p>
        {!validation.correct && validation.correctAnswer && (
          <p className="text-red-600 mt-1">
            Correct: <strong>{validation.correctAnswer}</strong>
          </p>
        )}
        {validation.feedback && (
          <p className={clsx(
            "text-sm mt-1",
            validation.correct ? "text-green-600" : "text-red-600"
          )}>
            {validation.feedback}
          </p>
        )}
      </div>

      {/* Streak indicator on correct */}
      {validation.correct && streak >= 2 && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="bg-orange-500 text-white font-bold px-3 py-1 rounded-full text-sm"
        >
          {streak}x streak!
        </motion.div>
      )}
    </motion.div>
  );
};

// Completion screen
const CompletionScreen: React.FC<{
  passed: boolean;
  correctCount: number;
  totalCount: number;
  xpEarned: number;
  onContinue: () => void;
  onRetry: () => void;
}> = ({ passed, correctCount, totalCount, xpEarned, onContinue, onRetry }) => {
  const percentage = Math.round((correctCount / Math.max(totalCount, 1)) * 100);
  const isPerfect = percentage === 100;
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-md mx-auto mt-8 text-center px-4"
    >
      <Confetti trigger={passed} particleCount={isPerfect ? 80 : 40} />
      
      <div className="bg-white rounded-3xl shadow-xl p-8 border border-gray-100">
        {/* Result icon */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', delay: 0.2 }}
          className={clsx(
            "w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6",
            passed 
              ? isPerfect ? "bg-gradient-to-br from-yellow-400 to-amber-500" : "bg-gradient-to-br from-green-400 to-emerald-500"
              : "bg-gradient-to-br from-red-400 to-red-500"
          )}
        >
          {passed ? (
            isPerfect ? <Crown size={48} color="white" /> : (
              <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            )
          ) : (
            <X size={48} className="text-white" />
          )}
        </motion.div>

        {/* Title */}
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-3xl font-black text-gray-900 mb-2"
        >
          {passed 
            ? isPerfect ? "Perfect!" : microcopy.lessonComplete()
            : "Out of Hearts"
          }
        </motion.h2>

        {/* Score */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="mb-6"
        >
          <div className={clsx(
            "text-6xl font-black mb-1",
            passed ? isPerfect ? "text-yellow-500" : "text-green-500" : "text-red-500"
          )}>
            {percentage}%
          </div>
          <p className="text-gray-500">{correctCount} of {totalCount} correct</p>
        </motion.div>

        {/* XP earned */}
        {passed && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-2 bg-yellow-100 text-yellow-700 font-bold px-4 py-2 rounded-xl mb-6"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l2.4 7.4h7.6l-6 4.6 2.3 7-6.3-4.6-6.3 4.6 2.3-7-6-4.6h7.6z" />
            </svg>
            +{xpEarned} XP earned
          </motion.div>
        )}

        {/* Actions */}
        <div className="space-y-3">
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            onClick={onContinue}
            className="w-full bg-[#58cc02] text-white font-bold py-4 px-6 rounded-2xl hover:bg-[#4db302] transition-colors shadow-lg border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px]"
          >
            Continue
          </motion.button>
          
          {!passed && (
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              onClick={onRetry}
              className="w-full bg-white text-gray-700 font-bold py-4 px-6 rounded-2xl hover:bg-gray-50 border-2 border-gray-200"
            >
              Try Again
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export const LessonSession: React.FC = () => {
  const { nodeId } = useParams<{ nodeId: string }>();
  const navigate = useNavigate();
  const { logger } = useComponentLogger('LessonSession');

  // Lesson state
  const [lesson, setLesson] = useState<LessonExercises | null>(null);
  const [grammarConfig, setGrammarConfig] = useState<GrammarConfig | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Module state
  const [modules, setModules] = useState<ModuleData[]>([]);
  const [currentModuleIdx, setCurrentModuleIdx] = useState(0);
  const [modulePhase, setModulePhase] = useState<ModulePhase>('teaching');
  const [teachingIdx, setTeachingIdx] = useState(0);
  
  // Exercise state
  const [exerciseIdx, setExerciseIdx] = useState(0);
  const [hearts, setHearts] = useState(MAX_HEARTS);
  const [results, setResults] = useState<ExerciseResult[]>([]);
  const [showFeedback, setShowFeedback] = useState<ValidationResult | null>(null);
  const [streak, setStreak] = useState(0);
  const [xpEarned, setXpEarned] = useState(0);
  
  // Celebration state
  const [showXP, setShowXP] = useState(false);
  const [lastXPGain, setLastXPGain] = useState(0);
  const [showSuccessBurst, setShowSuccessBurst] = useState(false);
  
  // Flow state
  const [showIntro, setShowIntro] = useState(true);
  const [completed, setCompleted] = useState(false);

  // Derived state
  const currentModule = useMemo(() => modules[currentModuleIdx] ?? null, [modules, currentModuleIdx]);
  const currentExercise = useMemo(() => currentModule?.exercises[exerciseIdx] ?? null, [currentModule, exerciseIdx]);
  const currentTeaching = useMemo(() => currentModule?.teaching[teachingIdx] ?? null, [currentModule, teachingIdx]);

  const totalExercises = useMemo(() => modules.reduce((sum, m) => sum + m.exercises.length, 0), [modules]);
  const completedExercises = useMemo(() => {
    let count = 0;
    for (let i = 0; i < currentModuleIdx; i++) count += modules[i].exercises.length;
    if (modulePhase === 'exercises') count += exerciseIdx;
    if (modulePhase === 'complete') count += currentModule?.exercises.length ?? 0;
    return count;
  }, [modules, currentModuleIdx, modulePhase, exerciseIdx, currentModule]);
  
  const overallProgress = useMemo(() => (totalExercises > 0 ? (completedExercises / totalExercises) * 100 : 0), [completedExercises, totalExercises]);
  const correctCount = useMemo(() => results.filter(r => r.correct).length, [results]);

  // Load lesson data
  useEffect(() => {
    if (!nodeId) return;

    const loadData = async () => {
      setLoading(true);
      try {
        const [exerciseData, grammar] = await Promise.all([
          getLessonExercises(nodeId),
          getGrammarConfig('ru'),
        ]);
        setLesson(exerciseData);
        setGrammarConfig(grammar);
        setModules(parseModulesFromLesson(exerciseData));
        logger.info('Lesson loaded', { nodeId });
      } catch (err) {
        logger.error('Failed to load lesson', err instanceof Error ? err : undefined);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [nodeId, logger]);

  const parseModulesFromLesson = (data: LessonExercises): ModuleData[] => {
    const content = data.content as Record<string, unknown> | undefined;
    
    if (content?.modules && Array.isArray(content.modules)) {
      return (content.modules as ModuleData[]).map((mod, idx) => ({
        id: mod.id || `mod_${idx + 1}`,
        title: mod.title || `Module ${idx + 1}`,
        type: mod.type || 'practice',
        teaching: mod.teaching || [],
        exercises: data.exercises.slice(
          Math.floor(idx * (data.exercises.length / (content.modules as unknown[]).length)),
          Math.floor((idx + 1) * (data.exercises.length / (content.modules as unknown[]).length))
        ),
      }));
    }
    
    const exerciseCount = data.exercises.length;
    const moduleSize = Math.ceil(exerciseCount / 5);
    const moduleTypes: ModuleType[] = ['intro', 'learn', 'pattern', 'practice', 'master'];
    const moduleTitles = ['Meet the Words', 'Learn More', 'Patterns', 'Practice', 'Master'];
    
    const generateTeaching = (): TeachingContent[] => {
      const teaching: TeachingContent[] = [];
      if (content?.introduction) {
        teaching.push({ type: 'explanation', title: 'Introduction', content: String(content.introduction) });
      }
      return teaching;
    };
    
    const mods: ModuleData[] = [];
    for (let i = 0; i < 5; i++) {
      const start = i * moduleSize;
      const end = Math.min(start + moduleSize, exerciseCount);
      const moduleExercises = data.exercises.slice(start, end);
      if (moduleExercises.length === 0 && i > 0) continue;
      mods.push({
        id: `mod_${i + 1}`,
        title: moduleTitles[i],
        type: moduleTypes[i],
        teaching: i === 0 ? generateTeaching() : [],
        exercises: moduleExercises,
      });
    }
    
    return mods.length > 0 ? mods : [{
      id: 'mod_1',
      title: 'Practice',
      type: 'practice',
      teaching: generateTeaching(),
      exercises: data.exercises,
    }];
  };

  const nextTeaching = useCallback(() => {
    if (!currentModule) return;
    if (teachingIdx < currentModule.teaching.length - 1) {
      setTeachingIdx(prev => prev + 1);
    } else {
      setModulePhase('exercises');
      setExerciseIdx(0);
    }
  }, [currentModule, teachingIdx]);

  const prevTeaching = useCallback(() => {
    if (teachingIdx > 0) setTeachingIdx(prev => prev - 1);
  }, [teachingIdx]);

  const validateAnswer = useCallback((answer: string | string[], exercise: Exercise): ValidationResult => {
    const normalize = (s: string) => s.toLowerCase().trim().replace(/[.,!?;:]/g, '');

    switch (exercise.type) {
      case 'word_bank':
        return { correct: normalize(answer as string) === normalize(exercise.targetText), correctAnswer: exercise.targetText };

      case 'typing': {
        const normalizedAnswer = normalize(answer as string);
        const isCorrect = exercise.acceptableAnswers.some(acc => normalize(acc) === normalizedAnswer) || normalize(exercise.targetText) === normalizedAnswer;
        const typoDetected = !isCorrect && levenshtein(normalizedAnswer, normalize(exercise.targetText)) <= 2;
        return { correct: isCorrect || typoDetected, correctAnswer: exercise.targetText, typoDetected };
      }

      case 'multiple_choice':
        return { correct: answer === exercise.correctAnswer, correctAnswer: exercise.correctAnswer };

      case 'fill_blank':
        return { correct: answer === exercise.correctAnswer, correctAnswer: exercise.correctAnswer };

      case 'matching':
        return { correct: true, correctAnswer: '' };

      case 'pattern_fill':
        return {
          correct: answer === exercise.correctEnding,
          correctAnswer: exercise.fullForm,
          feedback: answer === exercise.correctEnding
            ? `${exercise.stem}${exercise.correctEnding} = ${exercise.translation}`
            : `The ${exercise.targetCase} ending is -${exercise.correctEnding}`,
        };

      case 'pattern_apply':
        return {
          correct: answer === exercise.correctAnswer,
          correctAnswer: exercise.correctAnswer,
          feedback: answer === exercise.correctAnswer
            ? `Like ${exercise.exampleWord} → ${exercise.exampleForm}`
            : `Following the pattern: ${exercise.newWord} → ${exercise.correctAnswer}`,
        };

      case 'paradigm_complete': {
        const answerArr = Array.isArray(answer) ? answer : [answer];
        const correctForms = exercise.blankIndices.map(idx => exercise.cells[idx].form);
        const allCorrect = answerArr.every((a, i) => a === correctForms[i]);
        return { correct: allCorrect, correctAnswer: correctForms.join(', ') };
      }

      case 'dialogue_translate': {
        const normalizedAnswer = normalize(answer as string);
        const isCorrect = normalizedAnswer === normalize(exercise.targetText);
        const typoDetected = !isCorrect && levenshtein(normalizedAnswer, normalize(exercise.targetText)) <= 2;
        return { correct: isCorrect || typoDetected, correctAnswer: exercise.targetText, typoDetected };
      }

      default:
        return { correct: false, correctAnswer: '' };
    }
  }, []);

  const nextModule = useCallback(() => {
    if (currentModuleIdx < modules.length - 1) {
      const nextIdx = currentModuleIdx + 1;
      const nextMod = modules[nextIdx];
      setCurrentModuleIdx(nextIdx);
      setTeachingIdx(0);
      setExerciseIdx(0);
      setModulePhase(nextMod?.teaching?.length > 0 ? 'teaching' : 'exercises');
    } else {
      finishLesson();
    }
  }, [currentModuleIdx, modules]);

  const finishLesson = useCallback(async () => {
    if (!lesson || !nodeId) return;
    setCompleted(true);
    const correct = results.filter(r => r.correct).length;
    
    // Calculate final XP
    const baseXP = correct * XP_PER_EXERCISE;
    const perfectBonus = correct === results.length ? XP_PERFECT_BONUS : 0;
    const totalXP = baseXP + perfectBonus;
    setXpEarned(totalXP);
    
    try {
      await completeLesson(nodeId, correct, totalExercises);
      logger.info('Lesson completed', { correct, total: totalExercises, xp: totalXP });
    } catch (err) {
      logger.error('Failed to submit results', err instanceof Error ? err : undefined);
    }
  }, [lesson, nodeId, results, totalExercises, logger]);

  const handleSubmit = useCallback((answer: string | string[]) => {
    if (!currentExercise || !currentModule) return;

    const validation = validateAnswer(answer, currentExercise);
    setShowFeedback(validation);

    const result: ExerciseResult = { 
      exerciseId: currentExercise.id, 
      correct: validation.correct, 
      userAnswer: answer, 
      timeSpentMs: 0, 
      attempts: 1 
    };
    setResults(prev => [...prev, result]);

    if (validation.correct) {
      const newStreak = streak + 1;
      setStreak(newStreak);
      
      // XP calculation
      const xp = XP_PER_EXERCISE + (newStreak >= 3 ? XP_BONUS_STREAK : 0);
      setXpEarned(prev => prev + xp);
      setLastXPGain(xp);
      
      // Celebrations
      setShowSuccessBurst(true);
      setTimeout(() => setShowSuccessBurst(false), 300);
      
      if (newStreak >= 3) {
        setShowXP(true);
        setTimeout(() => setShowXP(false), 1200);
      }
    } else {
      setStreak(0);
      setHearts(prev => prev - 1);
    }

    setTimeout(() => {
      setShowFeedback(null);
      if (hearts <= 1 && !validation.correct) {
        setCompleted(true);
      } else if (exerciseIdx < currentModule.exercises.length - 1) {
        setExerciseIdx(prev => prev + 1);
      } else {
        setModulePhase('complete');
        setTimeout(nextModule, 800);
      }
    }, validation.correct ? 800 : 1500);
  }, [currentExercise, currentModule, validateAnswer, hearts, exerciseIdx, nextModule, streak]);

  const resetLesson = useCallback(() => {
    setCompleted(false);
    setCurrentModuleIdx(0);
    setModulePhase('teaching');
    setTeachingIdx(0);
    setExerciseIdx(0);
    setHearts(MAX_HEARTS);
    setResults([]);
    setStreak(0);
    setXpEarned(0);
    setShowIntro(true);
  }, []);

  const renderExercise = useCallback((exercise: Exercise) => {
    const baseProps = { exercise, onSubmit: handleSubmit, disabled: !!showFeedback, grammarConfig: grammarConfig ?? undefined };

    switch (exercise.type) {
      case 'word_bank': return <WordBank {...baseProps} exercise={exercise} />;
      case 'typing': return <Typing {...baseProps} exercise={exercise} />;
      case 'matching': return <Matching {...baseProps} exercise={exercise} />;
      case 'multiple_choice': return <MultipleChoice {...baseProps} exercise={exercise} />;
      case 'fill_blank': return <FillBlank {...baseProps} exercise={exercise} />;
      case 'pattern_fill': return <PatternFill {...baseProps} exercise={exercise} />;
      case 'pattern_apply': return <PatternApply {...baseProps} exercise={exercise} />;
      case 'paradigm_complete': return <ParadigmComplete {...baseProps} exercise={exercise} />;
      case 'dialogue_translate': return <DialogueTranslate {...baseProps} exercise={exercise} />;
      default: return <div>Unknown exercise type</div>;
    }
  }, [handleSubmit, showFeedback, grammarConfig]);

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-primary-500 rounded-full"
        />
        <p className="text-gray-500 font-medium">{microcopy.loading()}</p>
      </div>
    );
  }

  // Not found
  if (!lesson) {
    return (
      <div className="text-center mt-12">
        <Mascot mood="thinking" size={80} />
        <h2 className="text-2xl font-bold text-gray-900 mt-4">Lesson not found</h2>
        <button onClick={() => navigate('/')} className="mt-4 text-primary-600 hover:underline font-medium">
          Return Home
        </button>
      </div>
    );
  }

  // No content
  if (modules.length === 0 || totalExercises === 0) {
    return (
      <div className="text-center mt-12 max-w-md mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <Mascot mood="thinking" size={80} />
          <h2 className="text-2xl font-bold text-gray-900 mt-4 mb-2">{lesson.node_title}</h2>
          <p className="text-gray-500 mb-6">{microcopy.noContent()} Check back soon!</p>
          <button onClick={() => navigate('/')} className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800">
            Return to Path
          </button>
        </div>
      </div>
    );
  }

  // Intro screen
  if (showIntro) {
    return (
      <LessonIntro
        title={lesson.node_title}
        description={`${modules.length} modules · ${totalExercises} exercises`}
        content={lesson.content || {}}
        vocabulary={lesson.vocabulary}
        moduleCount={modules.length}
        exerciseCount={totalExercises}
        onStart={() => {
          setShowIntro(false);
          setModulePhase(currentModule?.teaching.length > 0 ? 'teaching' : 'exercises');
        }}
      />
    );
  }

  // Completion screen
  if (completed) {
    return (
      <CompletionScreen
        passed={hearts > 0}
        correctCount={correctCount}
        totalCount={results.length}
        xpEarned={xpEarned}
        onContinue={() => navigate('/')}
        onRetry={resetLesson}
      />
    );
  }

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col px-4">
      {/* Celebration effects */}
      <SuccessBurst trigger={showSuccessBurst} />
      <XPGain amount={lastXPGain} show={showXP} />

      {/* Header */}
      <div className="flex items-center justify-between mb-4 pt-4">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
          <X size={24} />
        </button>
        
        {/* Module dots */}
        <div className="flex items-center gap-2">
          {modules.map((mod, idx) => (
            <motion.div
              key={mod.id}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: idx * 0.1 }}
              className={clsx(
                "h-3 rounded-full transition-all",
                idx < currentModuleIdx ? "bg-green-500 w-3" :
                idx === currentModuleIdx ? "bg-primary-500 w-6" :
                "bg-gray-200 w-3"
              )}
            />
          ))}
        </div>

        {/* Hearts */}
        <div className="flex items-center gap-1">
          {Array.from({ length: MAX_HEARTS }).map((_, i) => (
            <Heart key={i} filled={i < hearts} breaking={i === hearts} />
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-6">
        <motion.div
          className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${overallProgress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Module title */}
      {currentModule && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-4"
        >
          <span className="text-xs font-bold text-primary-600 uppercase tracking-wider">
            Module {currentModuleIdx + 1}
          </span>
          <h2 className="text-xl font-bold text-gray-800">{currentModule.title}</h2>
        </motion.div>
      )}

      {/* Content area */}
      <div className="flex-1 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {/* Teaching phase */}
          {modulePhase === 'teaching' && currentTeaching && (
            <motion.div
              key={`teaching-${teachingIdx}`}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="flex-1 flex flex-col"
            >
              <div className="flex-1 overflow-y-auto py-4">
                <TeachingCard content={currentTeaching} />
              </div>
              
              <div className="flex items-center justify-between pt-4 pb-6 border-t border-gray-100 mt-4">
                <button
                  onClick={prevTeaching}
                  disabled={teachingIdx === 0}
                  className={clsx(
                    "flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all",
                    teachingIdx === 0 ? "text-gray-300" : "text-gray-600 hover:bg-gray-100"
                  )}
                >
                  <ChevronLeft size={20} /> Back
                </button>
                
                <span className="text-sm text-gray-400">
                  {teachingIdx + 1} / {currentModule?.teaching.length ?? 0}
                </span>
                
                <button
                  onClick={nextTeaching}
                  className="flex items-center gap-2 px-6 py-3 bg-[#58cc02] text-white font-bold rounded-xl hover:bg-[#4db302] transition-all border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px]"
                >
                  {teachingIdx < (currentModule?.teaching.length ?? 0) - 1 ? 'Next' : 'Start Practice'}
                  <ChevronRight size={20} />
                </button>
              </div>
            </motion.div>
          )}

          {/* Auto-skip to exercises if no teaching */}
          {modulePhase === 'teaching' && !currentTeaching && currentModule && (
            <motion.div
              key="no-teaching"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onAnimationComplete={() => setModulePhase('exercises')}
              className="flex-1 flex flex-col items-center justify-center"
            >
              <Mascot mood="encouraging" size={80} />
              <p className="text-gray-500 mt-4">{microcopy.continuePrompt()}</p>
            </motion.div>
          )}

          {/* Exercise phase */}
          {modulePhase === 'exercises' && currentExercise && (
            <motion.div
              key={`exercise-${currentExercise.id}`}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="flex-1 bg-white rounded-3xl shadow-xl border border-gray-100 p-8 flex flex-col"
            >
              {renderExercise(currentExercise)}
            </motion.div>
          )}

          {/* Module complete transition */}
          {modulePhase === 'complete' && (
            <motion.div
              key="module-complete"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex-1 flex flex-col items-center justify-center"
            >
              <Mascot mood="celebrating" size={100} />
              <p className="text-xl font-bold text-gray-800 mt-4">{microcopy.moduleComplete()}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Exercise counter */}
      {modulePhase === 'exercises' && currentModule && (
        <div className="text-center py-4 text-sm text-gray-400">
          Exercise {exerciseIdx + 1} of {currentModule.exercises.length}
        </div>
      )}

      {/* Feedback overlay */}
      <AnimatePresence>
        {showFeedback && <FeedbackPanel validation={showFeedback} streak={streak} />}
      </AnimatePresence>
    </div>
  );
};

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
