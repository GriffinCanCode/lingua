import React from 'react';
import { motion } from 'framer-motion';
import { Lock, Star, Crown, AlertCircle, Check, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import { SkillRingWithContent } from './SkillRing';

export type NodeState = 'locked' | 'available' | 'current' | 'in_progress' | 'completed' | 'needs_practice' | 'crowned';

export interface SkillNodeData {
  id: string;
  title: string;
  description?: string;
  icon: React.ElementType;
  state: NodeState;
  level: number;
  maxLevel: number;
  patternCount: number;
  estimatedMinutes?: number;
}

interface SkillNodeProps {
  data: SkillNodeData;
  index: number;
  onClick: (node: SkillNodeData) => void;
}

const stateConfig: Record<NodeState, {
  ringColor: 'primary' | 'gold' | 'gray' | 'orange';
  dashed: boolean;
  glowing: boolean;
  glowColor: string;
  opacity: number;
  badge?: React.ReactNode;
}> = {
  locked: {
    ringColor: 'gray',
    dashed: true,
    glowing: false,
    glowColor: '',
    opacity: 0.5,
    badge: <Lock size={12} className="text-gray-400" />,
  },
  available: {
    ringColor: 'primary',
    dashed: false,
    glowing: true,
    glowColor: 'rgba(14, 165, 233, 0.3)',
    opacity: 1,
  },
  current: {
    ringColor: 'primary',
    dashed: false,
    glowing: true,
    glowColor: 'rgba(34, 197, 94, 0.4)',
    opacity: 1,
  },
  in_progress: {
    ringColor: 'primary',
    dashed: false,
    glowing: false,
    glowColor: '',
    opacity: 1,
  },
  completed: {
    ringColor: 'primary',
    dashed: false,
    glowing: false,
    glowColor: '',
    opacity: 1,
    badge: <Check size={12} className="text-green-500" />,
  },
  needs_practice: {
    ringColor: 'orange',
    dashed: false,
    glowing: true,
    glowColor: 'rgba(249, 115, 22, 0.3)',
    opacity: 1,
    badge: <AlertCircle size={12} className="text-orange-500" />,
  },
  crowned: {
    ringColor: 'gold',
    dashed: false,
    glowing: false,
    glowColor: '',
    opacity: 1,
    badge: <Crown size={14} className="text-amber-500" />,
  },
};

export const SkillNode: React.FC<SkillNodeProps> = ({ data, index, onClick }) => {
  const config = stateConfig[data.state];
  const Icon = data.icon;
  const isLocked = data.state === 'locked';
  const isCurrent = data.state === 'current';

  const handleClick = () => {
    if (isLocked) {
      // Shake animation handled by motion
      return;
    }
    onClick(data);
  };

  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      onClick={handleClick}
      whileTap={isLocked ? { x: [0, -4, 4, -4, 4, 0] } : { scale: 0.95 }}
      className={clsx(
        "relative flex flex-col items-center gap-3 p-4 rounded-2xl transition-all focus:outline-none focus:ring-4 focus:ring-primary-100",
        isLocked ? "cursor-not-allowed" : "cursor-pointer hover:bg-white/50",
        config.opacity < 1 && "grayscale"
      )}
      style={{ opacity: config.opacity }}
      aria-label={`${data.title}, ${data.state}, level ${data.level} of ${data.maxLevel}`}
    >
      {/* Node Ring with Icon */}
      <SkillRingWithContent
        level={data.level}
        maxLevel={data.maxLevel}
        size={80}
        strokeWidth={6}
        color={config.ringColor}
        dashed={config.dashed}
        glowing={config.glowing}
        glowColor={config.glowColor}
      >
        <div className={clsx(
          "w-14 h-14 rounded-full flex items-center justify-center shadow-lg",
          isLocked ? "bg-gray-200" : "bg-white"
        )}>
          <Icon size={28} className={clsx(
            isLocked ? "text-gray-400" : "text-primary-600"
          )} />
        </div>
      </SkillRingWithContent>

      {/* Badge (lock, check, crown, etc.) */}
      {config.badge && (
        <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-white shadow-md flex items-center justify-center">
          {config.badge}
        </div>
      )}

      {/* Current Indicator */}
      {isCurrent && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-3 left-1/2 transform -translate-x-1/2"
        >
          <div className="bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg animate-bounce">
            START
          </div>
        </motion.div>
      )}

      {/* Title & Info */}
      <div className="text-center">
        <h4 className={clsx(
          "font-bold text-sm",
          isLocked ? "text-gray-400" : "text-gray-900"
        )}>
          {data.title}
        </h4>
        {data.estimatedMinutes && !isLocked && (
          <p className="text-xs text-gray-400 mt-0.5">~{data.estimatedMinutes} min</p>
        )}
      </div>

      {/* Level Stars */}
      <div className="flex gap-0.5">
        {Array.from({ length: data.maxLevel }).map((_, i) => (
          <Star
            key={i}
            size={12}
            className={clsx(
              i < data.level
                ? data.state === 'crowned' ? "text-amber-400 fill-amber-400" : "text-primary-500 fill-primary-500"
                : "text-gray-200"
            )}
          />
        ))}
      </div>
    </motion.button>
  );
};

