import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Lock, Check, Crown } from 'lucide-react';
import clsx from 'clsx';

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

// Duolingo-style progress ring with segments
const LessonRing: React.FC<{
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  isActive?: boolean;
  isCompleted?: boolean;
  isLocked?: boolean;
  color?: string;
}> = ({ progress, size = 80, strokeWidth = 6, isActive, isCompleted, isLocked, color = '#58cc02' }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Background ring */}
      <svg width={size} height={size} className="absolute inset-0 transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={isLocked ? '#e5e7eb' : '#e5e7eb'}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress ring */}
        {!isLocked && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={isCompleted ? '#22c55e' : color}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            style={{ strokeDasharray: circumference }}
          />
        )}
      </svg>
      
      {/* Glow effect for active lesson */}
      {isActive && !isCompleted && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle, ${color}20 0%, transparent 70%)`,
          }}
          animate={{ scale: [1, 1.1, 1], opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </div>
  );
};

// Single lesson node with Duolingo-style ring
const LessonNode: React.FC<{
  node: LevelNode;
  index: number;
  isFirst: boolean;
  onClick: () => void;
}> = ({ node, index, isFirst, onClick }) => {
  const isLocked = node.status === 'locked';
  const isCompleted = node.status === 'completed';
  const isActive = node.status === 'available' || node.status === 'in_progress';
  
  // Module progress (default to 5 modules if not specified)
  const modulesTotal = node.modules_total ?? 5;
  const modulesCompleted = node.modules_completed ?? 0;
  const moduleProgress = isCompleted ? 100 : (modulesCompleted / modulesTotal) * 100;
  
  // Alternating zigzag pattern like Duolingo
  const offsetX = index % 2 === 0 ? 0 : 60;
  
  // Colors based on status
  const ringColor = isCompleted ? '#22c55e' : isActive ? '#58cc02' : '#9ca3af';

  return (
    <div className="relative flex flex-col items-center" style={{ marginLeft: offsetX }}>
      {/* Connector path to previous node */}
      {!isFirst && (
        <svg
          className="absolute -top-8 left-1/2"
          width="80"
          height="32"
          style={{ transform: `translateX(${index % 2 === 0 ? '-70px' : '-10px'})` }}
        >
          <path
            d={index % 2 === 0 
              ? "M 70 32 Q 40 16 10 0"
              : "M 10 32 Q 40 16 70 0"
            }
            stroke={isLocked ? '#e5e7eb' : isCompleted || isActive ? '#22c55e' : '#d1d5db'}
            strokeWidth="4"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
      )}

      {/* Main lesson ring button */}
      <motion.button
        onClick={onClick}
        disabled={isLocked}
        whileHover={!isLocked ? { scale: 1.05 } : {}}
        whileTap={!isLocked ? { scale: 0.95 } : {}}
        animate={isActive && !isCompleted ? { y: [0, -4, 0] } : {}}
        transition={isActive ? { duration: 1.5, repeat: Infinity } : {}}
        className={clsx(
          "relative flex items-center justify-center rounded-full transition-all",
          isLocked && "cursor-not-allowed",
          isActive && "shadow-lg"
        )}
      >
        <LessonRing
          progress={moduleProgress}
          size={isActive ? 88 : 76}
          strokeWidth={isActive ? 7 : 5}
          isActive={isActive}
          isCompleted={isCompleted}
          isLocked={isLocked}
          color={ringColor}
        />
        
        {/* Inner circle with icon/content */}
        <div
          className={clsx(
            "absolute rounded-full flex items-center justify-center font-black text-lg transition-all",
            isLocked && "bg-gray-100 text-gray-400",
            isCompleted && "bg-green-500 text-white",
            isActive && "bg-[#58cc02] text-white shadow-md"
          )}
          style={{
            width: isActive ? 64 : 56,
            height: isActive ? 64 : 56,
          }}
        >
          {isLocked ? (
            <Lock size={24} />
          ) : isCompleted ? (
            modulesCompleted >= modulesTotal ? (
              <Crown size={24} className="text-yellow-300" />
            ) : (
              <Check size={24} strokeWidth={3} />
            )
          ) : (
            <span className="text-xl">{node.level}</span>
          )}
        </div>

        {/* Module segment indicators */}
        {isActive && !isCompleted && modulesTotal > 0 && (
          <div className="absolute -bottom-6 flex gap-1">
            {Array.from({ length: modulesTotal }).map((_, i) => (
              <motion.div
                key={i}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className={clsx(
                  "w-2 h-2 rounded-full",
                  i < modulesCompleted ? "bg-green-500" : "bg-gray-300"
                )}
              />
            ))}
          </div>
        )}
      </motion.button>

      {/* Lesson title */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={clsx(
          "mt-3 text-center max-w-[100px]",
          isActive && "mt-8" // Extra margin for module dots
        )}
      >
        <p className={clsx(
          "text-sm font-bold truncate",
          isLocked ? "text-gray-400" :
          isCompleted ? "text-green-600" :
          isActive ? "text-gray-800" : "text-gray-500"
        )}>
          {node.title}
        </p>
        {isActive && !isCompleted && (
          <p className="text-xs text-gray-500 mt-0.5">
            {modulesCompleted}/{modulesTotal} modules
          </p>
        )}
      </motion.div>
    </div>
  );
};

export const UnitCard: React.FC<UnitCardProps> = ({
  title, description, unitNumber, nodes,
  isExpanded: initialExpanded = false, isCurrent = false, isLocked = false,
  completedCount, totalCount, onNodeClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(initialExpanded || isCurrent);
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const isComplete = completedCount === totalCount && totalCount > 0;
  const nextLevel = nodes.find(n => n.status === 'available' || n.status === 'in_progress');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "rounded-3xl overflow-hidden transition-all",
        isCurrent ? "bg-gradient-to-br from-green-500 to-emerald-600 shadow-xl shadow-green-200" :
        isLocked ? "bg-gray-100 opacity-60" :
        isComplete ? "bg-gradient-to-br from-yellow-400 to-amber-500 shadow-lg shadow-yellow-200" :
        "bg-white border border-gray-200 shadow-sm"
      )}
    >
      {/* Header */}
      <button
        onClick={() => !isLocked && setIsExpanded(!isExpanded)}
        disabled={isLocked}
        className={clsx("w-full p-6 flex items-center gap-4 text-left transition-colors", !isLocked && "hover:bg-white/10")}
      >
        {/* Unit badge with crown for completed */}
        <div className={clsx(
          "w-14 h-14 rounded-2xl flex items-center justify-center font-black text-xl shrink-0 relative",
          isCurrent ? "bg-white/20 text-white" :
          isComplete ? "bg-white/30 text-white" :
          isLocked ? "bg-gray-200 text-gray-400" :
          "bg-primary-100 text-primary-600"
        )}>
          {isComplete ? <Crown size={28} /> : unitNumber}
        </div>

        {/* Title & Description */}
        <div className="flex-1 min-w-0">
          <p className={clsx(
            "text-xs font-bold uppercase tracking-wider mb-1",
            isCurrent || isComplete ? "text-white/70" : "text-gray-400"
          )}>
            Unit {unitNumber} · {nodes.length} lessons
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

        {/* Progress ring for unit */}
        <div className="flex items-center gap-3 shrink-0">
          {!isLocked && (
            <div className="relative w-12 h-12">
              <LessonRing
                progress={progress}
                size={48}
                strokeWidth={4}
                isCompleted={isComplete}
                color={isCurrent ? '#ffffff' : isComplete ? '#fbbf24' : '#58cc02'}
              />
              <span className={clsx(
                "absolute inset-0 flex items-center justify-center text-xs font-bold",
                isCurrent || isComplete ? "text-white" : "text-gray-600"
              )}>
                {completedCount}/{totalCount}
              </span>
            </div>
          )}

          <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center", isCurrent || isComplete ? "bg-white/10" : "bg-gray-100")}>
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

      {/* Expanded Content - Duolingo-style path */}
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
              "px-6 pb-8 pt-4",
              isCurrent || isComplete ? "bg-white/5" : "bg-gradient-to-b from-gray-50 to-white"
            )}>
              {/* Lesson path */}
              <div className="flex flex-col items-center gap-10 py-4">
                {nodes.map((node, idx) => (
                  <LessonNode
                    key={node.id}
                    node={node}
                    index={idx}
                    isFirst={idx === 0}
                    onClick={() => onNodeClick(node)}
                  />
                ))}
              </div>

              {/* Quick start button */}
              {nextLevel && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={() => onNodeClick(nextLevel)}
                  className={clsx(
                    "w-full mt-6 py-4 rounded-2xl font-bold text-base transition-all shadow-lg",
                    isCurrent || isComplete
                      ? "bg-white text-green-600 hover:bg-white/90 shadow-white/20"
                      : "bg-[#58cc02] text-white hover:bg-[#4db302] shadow-green-300/50"
                  )}
                >
                  {nextLevel.status === 'in_progress' 
                    ? `Continue: ${nextLevel.title}` 
                    : nextLevel.level === 1 
                      ? 'Start Learning' 
                      : `Start: ${nextLevel.title}`
                  }
                </motion.button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
