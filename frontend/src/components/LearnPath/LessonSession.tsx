import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Heart, Trophy, Check, XCircle, ChevronRight, ChevronLeft } from 'lucide-react';
import clsx from 'clsx';

import { getLessonExercises, completeLesson, LessonExercises } from '../../services/curriculum';
import { getGrammarConfig, GrammarConfig } from '../../services/languages';
import { LessonIntro } from './LessonIntro';
import { TeachingCard } from '../Teaching';
import { useComponentLogger } from '../../lib/logger';
import {
  WordBank, Typing, Matching, MultipleChoice, FillBlank,
  PatternFill, PatternApply, ParadigmComplete,
} from '../Exercises';
import type { Exercise, ExerciseResult, ValidationResult } from '../../types/exercises';
import type { TeachingContent, ModuleType } from '../../types/teaching';

const MAX_HEARTS = 3;

// Phase within a module
type ModulePhase = 'teaching' | 'exercises' | 'complete';

// Module data from API
interface ModuleData {
  id: string;
  title: string;
  type: ModuleType;
  teaching: TeachingContent[];
  exercises: Exercise[];
}

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
  
  // Flow state
  const [showIntro, setShowIntro] = useState(true);
  const [completed, setCompleted] = useState(false);

  // Current module and exercise
  const currentModule = useMemo(() => modules[currentModuleIdx] ?? null, [modules, currentModuleIdx]);
  const currentExercise = useMemo(() => currentModule?.exercises[exerciseIdx] ?? null, [currentModule, exerciseIdx]);
  const currentTeaching = useMemo(() => currentModule?.teaching[teachingIdx] ?? null, [currentModule, teachingIdx]);

  // Progress calculations
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

  // Load lesson data and parse modules
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
        
        // Parse modules from lesson data or create a single default module
        const parsedModules = parseModulesFromLesson(exerciseData);
        setModules(parsedModules);
        
        logger.info('Lesson loaded', { nodeId, moduleCount: parsedModules.length });
      } catch (err) {
        logger.error('Failed to load lesson', err instanceof Error ? err : undefined);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [nodeId, logger]);

  // Parse modules from lesson data - supports both old and new format
  const parseModulesFromLesson = (data: LessonExercises): ModuleData[] => {
    // Check if lesson has module structure
    const content = data.content as Record<string, unknown> | undefined;
    
    if (content?.modules && Array.isArray(content.modules)) {
      // New module-based format
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
    
    // Legacy format: create module structure based on exercise count
    const exerciseCount = data.exercises.length;
    const moduleSize = Math.ceil(exerciseCount / 5);
    
    // Generate teaching content based on lesson content
    const generateTeaching = (): TeachingContent[] => {
      const teaching: TeachingContent[] = [];
      if (content?.introduction) {
        teaching.push({
          type: 'explanation',
          title: 'Introduction',
          content: String(content.introduction),
        });
      }
      return teaching;
    };
    
    // Create 5 modules from existing exercises
    const modules: ModuleData[] = [];
    const moduleTypes: ModuleType[] = ['intro', 'learn', 'pattern', 'practice', 'master'];
    const moduleTitles = ['Meet the Words', 'Learn More', 'Patterns', 'Practice', 'Master'];
    
    for (let i = 0; i < 5; i++) {
      const start = i * moduleSize;
      const end = Math.min(start + moduleSize, exerciseCount);
      const moduleExercises = data.exercises.slice(start, end);
      
      if (moduleExercises.length === 0 && i > 0) continue;
      
      modules.push({
        id: `mod_${i + 1}`,
        title: moduleTitles[i],
        type: moduleTypes[i],
        teaching: i === 0 ? generateTeaching() : [],
        exercises: moduleExercises,
      });
    }
    
    return modules.length > 0 ? modules : [{
      id: 'mod_1',
      title: 'Practice',
      type: 'practice',
      teaching: generateTeaching(),
      exercises: data.exercises,
    }];
  };

  // Handle teaching navigation
  const nextTeaching = useCallback(() => {
    if (!currentModule) return;
    
    if (teachingIdx < currentModule.teaching.length - 1) {
      setTeachingIdx(prev => prev + 1);
    } else {
      // Move to exercises phase
      setModulePhase('exercises');
      setExerciseIdx(0);
    }
  }, [currentModule, teachingIdx]);

  const prevTeaching = useCallback(() => {
    if (teachingIdx > 0) {
      setTeachingIdx(prev => prev - 1);
    }
  }, [teachingIdx]);

  // Validate answer
  const validateAnswer = useCallback((answer: string | string[], exercise: Exercise): ValidationResult => {
    const normalize = (s: string) => s.toLowerCase().trim().replace(/[.,!?;:]/g, '');

    switch (exercise.type) {
      case 'word_bank':
        return { correct: normalize(answer as string) === normalize(exercise.targetText), correctAnswer: exercise.targetText };

      case 'typing': {
        const normalizedAnswer = normalize(answer as string);
        const isCorrect = exercise.acceptableAnswers.some(acc => normalize(acc) === normalizedAnswer) || normalize(exercise.targetText) === normalizedAnswer;
        const typoDetected = !isCorrect && levenshtein(normalizedAnswer, normalize(exercise.targetText)) <= 2;
        return { correct: isCorrect || typoDetected, correctAnswer: exercise.targetText, typoDetected, feedback: typoDetected ? 'Almost! Watch your spelling.' : undefined };
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

      default:
        return { correct: false, correctAnswer: '' };
    }
  }, []);

  // Move to next module
  const nextModule = useCallback(() => {
    if (currentModuleIdx < modules.length - 1) {
      const nextIdx = currentModuleIdx + 1;
      const nextMod = modules[nextIdx];
      setCurrentModuleIdx(nextIdx);
      setTeachingIdx(0);
      setExerciseIdx(0);
      // Skip to exercises if no teaching content
      setModulePhase(nextMod?.teaching?.length > 0 ? 'teaching' : 'exercises');
    } else {
      // All modules complete
      finishLesson();
    }
  }, [currentModuleIdx, modules]);

  // Finish lesson
  const finishLesson = useCallback(async () => {
    if (!lesson || !nodeId) return;
    setCompleted(true);
    const correct = results.filter(r => r.correct).length;
    try {
      await completeLesson(nodeId, correct, totalExercises);
      logger.info('Lesson completed', { correct, total: totalExercises });
    } catch (err) {
      logger.error('Failed to submit results', err instanceof Error ? err : undefined);
    }
  }, [lesson, nodeId, results, totalExercises, logger]);

  // Handle exercise submission
  const handleSubmit = useCallback((answer: string | string[]) => {
    if (!currentExercise || !currentModule) return;

    const validation = validateAnswer(answer, currentExercise);
    setShowFeedback(validation);

    const result: ExerciseResult = { exerciseId: currentExercise.id, correct: validation.correct, userAnswer: answer, timeSpentMs: 0, attempts: 1 };
    setResults(prev => [...prev, result]);

    if (!validation.correct) setHearts(prev => prev - 1);

    setTimeout(() => {
      setShowFeedback(null);
      if (hearts <= 1 && !validation.correct) {
        setCompleted(true);
      } else if (exerciseIdx < currentModule.exercises.length - 1) {
        setExerciseIdx(prev => prev + 1);
      } else {
        // Module complete - show transition or move to next
        setModulePhase('complete');
        setTimeout(nextModule, 800);
      }
    }, validation.correct ? 800 : 1500);
  }, [currentExercise, currentModule, validateAnswer, hearts, exerciseIdx, nextModule]);

  // Render exercise
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
      default: return <div>Unknown exercise type</div>;
    }
  }, [handleSubmit, showFeedback, grammarConfig]);

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
        <button onClick={() => navigate('/')} className="mt-4 text-primary-600 hover:underline">Return Home</button>
      </div>
    );
  }

  // No content
  if (modules.length === 0 || totalExercises === 0) {
    return (
      <div className="text-center mt-12 max-w-md mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className="w-20 h-20 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">📚</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{lesson.node_title}</h2>
          <p className="text-gray-500 mb-6">This lesson is being prepared. Check back soon!</p>
          <button onClick={() => navigate('/')} className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800">Return to Path</button>
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
        onStart={() => {
          setShowIntro(false);
          setModulePhase(currentModule?.teaching.length > 0 ? 'teaching' : 'exercises');
        }}
      />
    );
  }

  // Completion screen
  if (completed) {
    const percentage = Math.round((correctCount / Math.max(results.length, 1)) * 100);
    const passed = hearts > 0;

    return (
      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="max-w-md mx-auto mt-12 text-center">
        <div className="bg-white rounded-3xl shadow-xl p-10 border border-gray-100">
          <div className={clsx("w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6", passed ? "bg-yellow-100 text-yellow-600" : "bg-red-100 text-red-600")}>
            {passed ? <Trophy size={48} /> : <XCircle size={48} />}
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">{passed ? 'Lesson Complete!' : 'Out of Hearts'}</h2>
          <div className={clsx("text-5xl font-black mb-2", passed ? "text-primary-600" : "text-red-500")}>{percentage}%</div>
          <p className="text-gray-500 mb-8">{correctCount} of {results.length} correct</p>
          <div className="space-y-3">
            <button onClick={() => navigate('/')} className="w-full bg-gray-900 text-white font-bold py-4 px-6 rounded-xl hover:bg-gray-800">Continue</button>
            <button onClick={() => { setCompleted(false); setCurrentModuleIdx(0); setModulePhase('teaching'); setTeachingIdx(0); setExerciseIdx(0); setHearts(MAX_HEARTS); setResults([]); setShowIntro(true); }} className="w-full bg-white text-gray-700 font-bold py-4 px-6 rounded-xl hover:bg-gray-50 border-2 border-gray-200">Try Again</button>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col px-4">
      {/* Header with module indicators */}
      <div className="flex items-center justify-between mb-4 pt-4">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500"><X size={24} /></button>
        
        {/* Module dots */}
        <div className="flex items-center gap-2">
          {modules.map((mod, idx) => (
            <div
              key={mod.id}
              className={clsx(
                "w-3 h-3 rounded-full transition-all",
                idx < currentModuleIdx ? "bg-green-500" :
                idx === currentModuleIdx ? "bg-primary-500 w-6" :
                "bg-gray-200"
              )}
            />
          ))}
        </div>

        <div className="flex items-center gap-1">
          {Array.from({ length: MAX_HEARTS }).map((_, i) => (
            <Heart key={i} size={20} className={clsx("transition-colors", i < hearts ? "fill-red-500 text-red-500" : "text-gray-300")} />
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-6">
        <motion.div className="h-full bg-primary-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${overallProgress}%` }} transition={{ duration: 0.3 }} />
      </div>

      {/* Module title */}
      {currentModule && (
        <div className="text-center mb-4">
          <span className="text-xs font-bold text-primary-600 uppercase tracking-wider">Module {currentModuleIdx + 1}</span>
          <h2 className="text-xl font-bold text-gray-800">{currentModule.title}</h2>
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {/* Teaching phase with content */}
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
              
              {/* Teaching navigation */}
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
                  className="flex items-center gap-2 px-6 py-3 bg-primary-500 text-white font-bold rounded-xl hover:bg-primary-600 transition-all"
                >
                  {teachingIdx < (currentModule?.teaching.length ?? 0) - 1 ? 'Next' : 'Start Practice'}
                  <ChevronRight size={20} />
                </button>
              </div>
            </motion.div>
          )}

          {/* Teaching phase but no content - auto-skip to exercises */}
          {modulePhase === 'teaching' && !currentTeaching && currentModule && (
            <motion.div
              key="no-teaching"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onAnimationComplete={() => setModulePhase('exercises')}
              className="flex-1 flex flex-col items-center justify-center"
            >
              <div className="text-center">
                <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <ChevronRight size={32} className="text-primary-600" />
                </div>
                <p className="text-gray-500">Starting exercises...</p>
              </div>
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

          {/* Exercise phase but no exercises - skip to next module */}
          {modulePhase === 'exercises' && !currentExercise && currentModule && (
            <motion.div
              key="no-exercises"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onAnimationComplete={() => {
                setModulePhase('complete');
                setTimeout(nextModule, 500);
              }}
              className="flex-1 flex flex-col items-center justify-center"
            >
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Check size={32} className="text-green-600" />
                </div>
                <p className="text-gray-500">Module complete!</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Exercise counter (during exercise phase) */}
      {modulePhase === 'exercises' && currentModule && (
        <div className="text-center py-4 text-sm text-gray-400">
          Exercise {exerciseIdx + 1} of {currentModule.exercises.length}
        </div>
      )}

      {/* Feedback overlay */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className={clsx("fixed bottom-0 left-0 right-0 p-6 flex items-center gap-4", showFeedback.correct ? "bg-green-100" : "bg-red-100")}
          >
            <div className={clsx("w-12 h-12 rounded-full flex items-center justify-center", showFeedback.correct ? "bg-green-500" : "bg-red-500")}>
              {showFeedback.correct ? <Check className="text-white" size={24} /> : <X className="text-white" size={24} />}
            </div>
            <div className="flex-1">
              <p className={clsx("font-bold text-lg", showFeedback.correct ? "text-green-700" : "text-red-700")}>
                {showFeedback.correct ? (showFeedback.typoDetected ? 'Almost correct!' : 'Correct!') : 'Incorrect'}
              </p>
              {!showFeedback.correct && <p className="text-red-600">Correct answer: <strong>{showFeedback.correctAnswer}</strong></p>}
              {showFeedback.feedback && <p className="text-gray-600 text-sm">{showFeedback.feedback}</p>}
            </div>
          </motion.div>
        )}
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
