import { motion } from 'framer-motion';
import clsx from 'clsx';

interface SkillRingProps {
  level: number; // 0-5
  maxLevel?: number;
  size?: number;
  strokeWidth?: number;
  color?: 'primary' | 'gold' | 'gray' | 'orange';
  dashed?: boolean;
  animated?: boolean;
}

const colorMap = {
  primary: { stroke: '#0ea5e9', bg: '#e0f2fe' },
  gold: { stroke: '#f59e0b', bg: '#fef3c7' },
  gray: { stroke: '#9ca3af', bg: '#f3f4f6' },
  orange: { stroke: '#f97316', bg: '#ffedd5' },
};

export const SkillRing: React.FC<SkillRingProps> = ({
  level,
  maxLevel = 5,
  size = 80,
  strokeWidth = 6,
  color = 'primary',
  dashed = false,
  animated = true,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(level / maxLevel, 1);
  const strokeDashoffset = circumference * (1 - progress);
  const colors = colorMap[color];

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      {/* Background ring */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={colors.bg}
        strokeWidth={strokeWidth}
        strokeDasharray={dashed ? '4 4' : undefined}
      />
      {/* Progress ring */}
      {level > 0 && (
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={animated ? { strokeDashoffset: circumference } : { strokeDashoffset }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.8, ease: [0.65, 0, 0.35, 1] }}
        />
      )}
    </svg>
  );
};

interface SkillRingWithContentProps extends SkillRingProps {
  children: React.ReactNode;
  glowColor?: string;
  glowing?: boolean;
}

export const SkillRingWithContent: React.FC<SkillRingWithContentProps> = ({
  children,
  glowing = false,
  glowColor = 'rgba(14, 165, 233, 0.4)',
  ...ringProps
}) => {
  const { size = 80 } = ringProps;
  
  return (
    <div 
      className={clsx(
        "relative flex items-center justify-center",
        glowing && "animate-pulse"
      )}
      style={{ width: size, height: size }}
    >
      {glowing && (
        <div 
          className="absolute inset-0 rounded-full blur-xl opacity-50"
          style={{ backgroundColor: glowColor }}
        />
      )}
      <SkillRing {...ringProps} />
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
};

