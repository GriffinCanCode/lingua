import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Layers } from 'lucide-react';
import clsx from 'clsx';
import { SkillNode, SkillNodeData } from './SkillNode';

interface UnitCardProps {
  id: string;
  title: string;
  description: string;
  unitNumber: number;
  nodes: SkillNodeData[];
  isExpanded?: boolean;
  isCurrent?: boolean;
  isLocked?: boolean;
  completedCount: number;
  totalCount: number;
  onNodeClick: (node: SkillNodeData) => void;
}

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
            Unit {unitNumber}
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
              <Layers size={20} className="text-gray-400" />
            ) : isExpanded ? (
              <ChevronUp size={20} className={isCurrent || isComplete ? "text-white" : "text-gray-600"} />
            ) : (
              <ChevronDown size={20} className={isCurrent || isComplete ? "text-white" : "text-gray-600"} />
            )}
          </div>
        </div>
      </button>

      {/* Expanded Content */}
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
              <div className="flex flex-wrap justify-center gap-2">
                {nodes.map((node, idx) => (
                  <SkillNode
                    key={node.id}
                    data={node}
                    index={idx}
                    onClick={onNodeClick}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

