import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Lock, Check, Star, Sparkles, BookOpen, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import { Crown, ProgressRing, Mascot } from '../Celebrations';
import { microcopy } from '../../lib/microcopy';

export interface LevelNode {
  id: string;
  title: string;
  level: number;
  level_type: 'intro' | 'easy' | 'medium' | 'hard' | 'review';
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  total_reviews: number;
  modules_completed?: number;
  modules_total?: number;
}

interface Unit {
  id: string;
  number: number;
  title: string;
  description: string;
  nodes: LevelNode[];
  isCurrent: boolean;
  isLocked: boolean;
  isComplete: boolean;
}

interface UnitViewProps {
  unit: Unit;
  onBack: () => void;
  onNodeClick: (node: LevelNode) => void;
  onComplete?: () => void;
}

// Theme colors for lesson types
const THEMES: Record<string, { bg: string; border: string; text: string; light: string }> = {
  intro: { bg: 'bg-sky-500', border: 'border-sky-400', text: 'text-sky-600', light: 'bg-sky-100' },
  easy: { bg: 'bg-green-500', border: 'border-green-400', text: 'text-green-600', light: 'bg-green-100' },
  medium: { bg: 'bg-amber-500', border: 'border-amber-400', text: 'text-amber-600', light: 'bg-amber-100' },
  hard: { bg: 'bg-purple-500', border: 'border-purple-400', text: 'text-purple-600', light: 'bg-purple-100' },
  review: { bg: 'bg-rose-500', border: 'border-rose-400', text: 'text-rose-600', light: 'bg-rose-100' },
};

// Lesson icon based on type
const getLessonIcon = (type: LevelNode['level_type']) => {
  switch (type) {
    case 'intro': return BookOpen;
    case 'review': return Star;
    default: return Sparkles;
  }
};

// Single lesson node in the path
const LessonNode: React.FC<{
  node: LevelNode;
  index: number;
  total: number;
  isFirstAvailable: boolean;
  onClick: () => void;
}> = ({ node, index, total, isFirstAvailable, onClick }) => {
  const nodeRef = useRef<HTMLButtonElement>(null);
  const isLocked = node.status === 'locked';
  const isCompleted = node.status === 'completed';
  const isActive = node.status === 'available' || node.status === 'in_progress';
  const theme = THEMES[node.level_type] || THEMES.easy;
  const Icon = getLessonIcon(node.level_type);
  
  // Scroll into view if this is the first available lesson
  useEffect(() => {
    if (isFirstAvailable && nodeRef.current) {
      nodeRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isFirstAvailable]);

  // Sinusoidal path offset for visual interest
  const amplitude = 50;
  const offsetX = Math.sin((index / (total - 1 || 1)) * Math.PI * 2) * amplitude;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.03, type: 'spring', stiffness: 300, damping: 25 }}
      className="relative flex flex-col items-center"
      style={{ marginLeft: offsetX }}
    >
      {/* Connector to next */}
      {index < total - 1 && (
        <svg
          className="absolute top-full left-1/2 -translate-x-1/2 z-0"
          width="100"
          height="60"
          style={{ marginTop: -4 }}
        >
          <motion.path
            d={`M 50 0 Q ${50 + (Math.sin(((index + 0.5) / (total - 1 || 1)) * Math.PI * 2) * amplitude - offsetX)} 30 ${50 + (Math.sin(((index + 1) / (total - 1 || 1)) * Math.PI * 2) * amplitude - offsetX)} 60`}
            stroke={isCompleted ? '#22c55e' : '#e5e7eb'}
            strokeWidth="4"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={isCompleted ? "0" : "8 8"}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: index * 0.03 + 0.1, duration: 0.3 }}
          />
        </svg>
      )}

      {/* Lesson button */}
      <motion.button
        ref={nodeRef}
        onClick={onClick}
        disabled={isLocked}
        whileHover={!isLocked ? { scale: 1.1 } : {}}
        whileTap={!isLocked ? { scale: 0.95 } : {}}
        className={clsx(
          "relative z-10 w-16 h-16 rounded-full flex items-center justify-center transition-all",
          isLocked && "cursor-not-allowed",
          isCompleted && "bg-green-500 shadow-lg shadow-green-200",
          isActive && `${theme.bg} shadow-xl shadow-${theme.bg.replace('bg-', '')}/30`,
          !isLocked && !isCompleted && !isActive && "bg-gray-100"
        )}
      >
        {isLocked ? (
          <Lock size={22} className="text-gray-300" />
        ) : isCompleted ? (
          <Check size={26} strokeWidth={3} className="text-white" />
        ) : (
          <Icon size={24} className="text-white" />
        )}

        {/* Pulse ring for active */}
        {isActive && (
          <motion.div
            className={clsx("absolute inset-0 rounded-full", theme.bg)}
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}

        {/* Star badge for first available */}
        {isFirstAvailable && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1, rotate: [0, 10, -10, 0] }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center shadow-lg"
          >
            <Star size={14} className="text-yellow-700" fill="currentColor" />
          </motion.div>
        )}
      </motion.button>

      {/* Lesson number & title */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.03 + 0.1 }}
        className="mt-3 text-center max-w-[120px]"
      >
        <p className={clsx(
          "text-xs font-bold uppercase tracking-wide mb-0.5",
          isLocked ? "text-gray-300" :
          isCompleted ? "text-green-500" :
          isActive ? theme.text : "text-gray-400"
        )}>
          Lesson {index + 1}
        </p>
        <p className={clsx(
          "text-sm font-semibold leading-tight",
          isLocked ? "text-gray-300" :
          isCompleted ? "text-gray-600" :
          isActive ? "text-gray-800" : "text-gray-400"
        )}>
          {node.title}
        </p>
      </motion.div>
    </motion.div>
  );
};

// Full screen unit view
export const UnitView: React.FC<UnitViewProps> = ({ unit, onBack, onNodeClick, onComplete }) => {
  const completedCount = unit.nodes.filter(n => n.status === 'completed').length;
  const progress = unit.nodes.length > 0 ? (completedCount / unit.nodes.length) * 100 : 0;
  const nextLesson = unit.nodes.find(n => n.status === 'available' || n.status === 'in_progress');
  const firstAvailableIdx = unit.nodes.findIndex(n => n.status === 'available' || n.status === 'in_progress');
  
  const headerGradient = unit.isComplete
    ? "from-amber-500 via-yellow-400 to-orange-400"
    : "from-emerald-500 via-green-500 to-teal-500";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen -m-4 md:-m-6 flex flex-col"
    >
      {/* Header */}
      <div className={clsx("bg-gradient-to-r p-6 pb-8", headerGradient)}>
        <div className="flex items-center justify-between mb-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onBack}
            className="flex items-center gap-2 text-white/90 hover:text-white font-medium"
          >
            <ArrowLeft size={20} />
            <span>Back</span>
          </motion.button>
          
          <ProgressRing
            progress={progress}
            size={44}
            strokeWidth={4}
            color="#ffffff"
            bgColor="rgba(255,255,255,0.3)"
          >
            <span className="text-xs font-bold text-white">{completedCount}/{unit.nodes.length}</span>
          </ProgressRing>
        </div>

        <div className="flex items-center gap-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
            className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center"
          >
            {unit.isComplete ? (
              <Crown size={32} color="white" />
            ) : (
              <span className="text-3xl font-black text-white">{unit.number}</span>
            )}
          </motion.div>
          <div>
            <p className="text-white/70 text-sm font-medium">Unit {unit.number}</p>
            <h1 className="text-2xl font-black text-white">{unit.title}</h1>
            <p className="text-white/80 text-sm mt-0.5">{unit.description}</p>
          </div>
        </div>
      </div>

      {/* Lesson path */}
      <div className="flex-1 bg-gray-50 px-6 py-8 overflow-y-auto">
        <div className="max-w-md mx-auto">
          {/* Start mascot */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <Mascot mood={unit.isComplete ? "celebrating" : "encouraging"} size={60} />
            <p className="text-gray-500 font-medium mt-2">
              {unit.isComplete ? "Unit mastered! 🎉" : microcopy.lessonHook()}
            </p>
          </motion.div>

          {/* Lessons */}
          <div className="flex flex-col items-center gap-12">
            {unit.nodes.map((node, idx) => (
              <LessonNode
                key={node.id}
                node={node}
                index={idx}
                total={unit.nodes.length}
                isFirstAvailable={idx === firstAvailableIdx}
                onClick={() => onNodeClick(node)}
              />
            ))}
          </div>

          {/* End trophy */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: unit.nodes.length * 0.03 + 0.2 }}
            className="flex flex-col items-center mt-12 mb-8"
          >
            <div className={clsx(
              "w-20 h-20 rounded-full flex items-center justify-center",
              unit.isComplete
                ? "bg-gradient-to-br from-yellow-400 to-amber-500 shadow-xl shadow-amber-200"
                : "bg-gray-200"
            )}>
              <Crown size={36} color={unit.isComplete ? "white" : "#d1d5db"} />
            </div>
            <p className={clsx(
              "font-bold mt-3",
              unit.isComplete ? "text-amber-600" : "text-gray-400"
            )}>
              {unit.isComplete ? "Unit Complete!" : "Complete all lessons"}
            </p>
          </motion.div>
        </div>
      </div>

      {/* Bottom CTA */}
      {nextLesson && (
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="sticky bottom-0 bg-white border-t border-gray-200 p-4 shadow-lg"
        >
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onNodeClick(nextLesson)}
            className="w-full bg-[#58cc02] text-white font-bold py-4 px-6 rounded-2xl hover:bg-[#4db302] border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px] flex items-center justify-center gap-3 text-lg shadow-lg shadow-green-200"
          >
            <Sparkles size={22} />
            {nextLesson.status === 'in_progress' ? 'Continue' : 'Start'}: {nextLesson.title}
            <ChevronRight size={22} />
          </motion.button>
        </motion.div>
      )}

      {/* Complete button for finished units */}
      {unit.isComplete && onComplete && (
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="sticky bottom-0 bg-white border-t border-gray-200 p-4"
        >
          <button
            onClick={onComplete}
            className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-white font-bold py-4 px-6 rounded-2xl flex items-center justify-center gap-2 text-lg shadow-lg"
          >
            <Crown size={22} />
            Continue to Next Unit
            <ChevronRight size={22} />
          </button>
        </motion.div>
      )}
    </motion.div>
  );
};

export { UnitView as UnitCard };
