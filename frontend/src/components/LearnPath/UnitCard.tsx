import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Lock, Star, Zap, Target, Award, Check, Lightbulb } from 'lucide-react';
import clsx from 'clsx';

export interface LevelNode {
  id: string;
  title: string;
  level: number;
  level_type: 'intro' | 'easy' | 'medium' | 'hard' | 'review';
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  total_reviews: number;
  estimated_duration_min: number;
}

interface UnitCardProps {
  id: string;
  title: string;
  description: string;
  unitNumber: number;
  nodes: LevelNode[];
  isExpanded?: boolean;
  isCurrent?: boolean;
  isLocked?: boolean;
  completedCount: number;
  totalCount: number;
  onNodeClick: (node: LevelNode) => void;
}

// Level type styling and icons
const LEVEL_CONFIG: Record<string, { icon: React.ReactNode; color: string; bgColor: string; label: string }> = {
  intro: {
    icon: <Lightbulb size={16} />,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100 border-yellow-300',
    label: 'Learn',
  },
  easy: {
    icon: <Star size={16} />,
    color: 'text-green-600',
    bgColor: 'bg-green-100 border-green-300',
    label: 'Easy',
  },
  medium: {
    icon: <Zap size={16} />,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 border-blue-300',
    label: 'Medium',
  },
  hard: {
    icon: <Target size={16} />,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 border-purple-300',
    label: 'Hard',
  },
  review: {
    icon: <Award size={16} />,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100 border-orange-300',
    label: 'Review',
  },
};

const LevelBubble: React.FC<{
  node: LevelNode;
  isFirst: boolean;
  onClick: () => void;
}> = ({ node, isFirst, onClick }) => {
  const config = LEVEL_CONFIG[node.level_type] || LEVEL_CONFIG.medium;
  const isLocked = node.status === 'locked';
  const isCompleted = node.status === 'completed';
  const isActive = node.status === 'available' || node.status === 'in_progress';

  return (
    <div className="flex flex-col items-center">
      {/* Connector line (except for first) */}
      {!isFirst && (
        <div className={clsx(
          "w-8 h-1 -mt-1 mb-1 rounded-full",
          isLocked ? "bg-gray-200" : isCompleted ? "bg-green-400" : "bg-gray-300"
        )} />
      )}

      <motion.button
        whileHover={!isLocked ? { scale: 1.1 } : {}}
        whileTap={!isLocked ? { scale: 0.95 } : {}}
        onClick={onClick}
        disabled={isLocked}
        className={clsx(
          "relative w-14 h-14 rounded-full flex items-center justify-center border-2 transition-all",
          isLocked && "bg-gray-100 border-gray-200 text-gray-300 cursor-not-allowed",
          isCompleted && "bg-green-500 border-green-600 text-white",
          isActive && `${config.bgColor} ${config.color} border-2 shadow-lg`,
        )}
      >
        {isLocked ? (
          <Lock size={18} />
        ) : isCompleted ? (
          <Check size={20} strokeWidth={3} />
        ) : (
          config.icon
        )}

        {/* Level number badge */}
        <span className={clsx(
          "absolute -top-1 -right-1 w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center",
          isLocked ? "bg-gray-200 text-gray-400" :
          isCompleted ? "bg-green-700 text-white" :
          "bg-white border border-gray-200 text-gray-600"
        )}>
          {node.level}
        </span>
      </motion.button>

      {/* Label */}
      <span className={clsx(
        "mt-2 text-xs font-medium",
        isLocked ? "text-gray-300" :
        isCompleted ? "text-green-600" :
        isActive ? config.color : "text-gray-500"
      )}>
        {config.label}
      </span>
    </div>
  );
};

export const UnitCard: React.FC<UnitCardProps> = ({
  title,
  description,
  unitNumber,
  nodes,
  isExpanded: initialExpanded = false,
  isCurrent = false,
  isLocked = false,
  completedCount,
  totalCount,
  onNodeClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(initialExpanded || isCurrent);
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const isComplete = completedCount === totalCount && totalCount > 0;

  // Find the next available level
  const nextLevel = nodes.find(n => n.status === 'available' || n.status === 'in_progress');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "rounded-3xl overflow-hidden transition-all",
        isCurrent
          ? "bg-gradient-to-br from-green-500 to-emerald-600 shadow-xl shadow-green-200"
          : isLocked
            ? "bg-gray-100 opacity-60"
            : isComplete
              ? "bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg"
              : "bg-white border border-gray-200 shadow-sm"
      )}
    >
      {/* Header */}
      <button
        onClick={() => !isLocked && setIsExpanded(!isExpanded)}
        disabled={isLocked}
        className={clsx(
          "w-full p-6 flex items-center gap-4 text-left transition-colors",
          !isLocked && "hover:bg-white/10"
        )}
      >
        {/* Unit Number Badge */}
        <div className={clsx(
          "w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl shrink-0",
          isCurrent || isComplete
            ? "bg-white/20 text-white"
            : isLocked
              ? "bg-gray-200 text-gray-400"
              : "bg-primary-100 text-primary-600"
        )}>
          {unitNumber}
        </div>

        {/* Title & Description */}
        <div className="flex-1 min-w-0">
          <p className={clsx(
            "text-xs font-bold uppercase tracking-wider mb-1",
            isCurrent || isComplete ? "text-white/70" : "text-gray-400"
          )}>
            Unit {unitNumber} · {nodes.length} levels
          </p>
          <h3 className={clsx(
            "font-bold text-lg truncate",
            isCurrent || isComplete ? "text-white" : isLocked ? "text-gray-400" : "text-gray-900"
          )}>
            {title}
          </h3>
          <p className={clsx(
            "text-sm truncate mt-0.5",
            isCurrent || isComplete ? "text-white/80" : "text-gray-500"
          )}>
            {description}
          </p>
        </div>

        {/* Progress & Expand */}
        <div className="flex items-center gap-3 shrink-0">
          {!isLocked && (
            <div className="text-right">
              <div className={clsx(
                "text-xs font-bold",
                isCurrent || isComplete ? "text-white/70" : "text-gray-400"
              )}>
                {completedCount}/{totalCount}
              </div>
              <div className={clsx(
                "w-16 h-2 rounded-full overflow-hidden mt-1",
                isCurrent || isComplete ? "bg-white/20" : "bg-gray-200"
              )}>
                <motion.div
                  className={clsx(
                    "h-full rounded-full",
                    isCurrent || isComplete ? "bg-white" : "bg-primary-500"
                  )}
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          )}

          <div className={clsx(
            "w-10 h-10 rounded-xl flex items-center justify-center",
            isCurrent || isComplete ? "bg-white/10" : "bg-gray-100"
          )}>
            {isLocked ? (
              <Lock size={20} className="text-gray-400" />
            ) : isExpanded ? (
              <ChevronUp size={20} className={isCurrent || isComplete ? "text-white" : "text-gray-600"} />
            ) : (
              <ChevronDown size={20} className={isCurrent || isComplete ? "text-white" : "text-gray-600"} />
            )}
          </div>
        </div>
      </button>

      {/* Expanded Content - Level Bubbles */}
      <AnimatePresence>
        {isExpanded && !isLocked && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className={clsx(
              "p-6 pt-2",
              isCurrent || isComplete ? "bg-white/10" : "bg-gray-50"
            )}>
              {/* Level bubbles in a row */}
              <div className="flex items-start justify-center gap-4 overflow-x-auto pb-2">
                {nodes.map((node, idx) => (
                  <LevelBubble
                    key={node.id}
                    node={node}
                    isFirst={idx === 0}
                    onClick={() => onNodeClick(node)}
                  />
                ))}
              </div>

              {/* Quick start button for next level */}
              {nextLevel && (
                <button
                  onClick={() => onNodeClick(nextLevel)}
                  className={clsx(
                    "w-full mt-4 py-3 rounded-xl font-bold text-sm transition-all",
                    isCurrent || isComplete
                      ? "bg-white text-green-600 hover:bg-white/90"
                      : "bg-primary-500 text-white hover:bg-primary-600"
                  )}
                >
                  {nextLevel.level === 1 ? 'Start Learning' : `Continue Level ${nextLevel.level}`}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
