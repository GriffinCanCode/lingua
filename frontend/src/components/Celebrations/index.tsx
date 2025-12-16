/**
 * Celebration Components - Duolingo-style visual feedback
 * Particles, confetti, XP animations - no emojis
 */
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

// Particle types for variety
type ParticleShape = 'circle' | 'square' | 'star' | 'diamond';

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  color: string;
  shape: ParticleShape;
  rotation: number;
  velocity: { x: number; y: number };
}

// Color palettes
const CELEBRATION_COLORS = ['#58cc02', '#ffc800', '#ff4b4b', '#1cb0f6', '#ce82ff'];
const SUCCESS_COLORS = ['#58cc02', '#89e219', '#a5ed3d', '#c8f76f'];

const createParticle = (index: number, colors: string[], originX = 50, originY = 50): Particle => ({
  id: index,
  x: originX + (Math.random() - 0.5) * 20,
  y: originY,
  size: 4 + Math.random() * 8,
  color: colors[Math.floor(Math.random() * colors.length)],
  shape: (['circle', 'square', 'star', 'diamond'] as ParticleShape[])[Math.floor(Math.random() * 4)],
  rotation: Math.random() * 360,
  velocity: {
    x: (Math.random() - 0.5) * 15,
    y: -8 - Math.random() * 12,
  },
});

// SVG shapes for particles
const ParticleShape: React.FC<{ shape: ParticleShape; size: number; color: string }> = ({ shape, size, color }) => {
  switch (shape) {
    case 'star':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
          <path d="M12 2l2.4 7.4h7.6l-6 4.6 2.3 7-6.3-4.6-6.3 4.6 2.3-7-6-4.6h7.6z" />
        </svg>
      );
    case 'diamond':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
          <path d="M12 2l10 10-10 10L2 12z" />
        </svg>
      );
    case 'square':
      return <div style={{ width: size, height: size, backgroundColor: color, borderRadius: 2 }} />;
    default:
      return <div style={{ width: size, height: size, backgroundColor: color, borderRadius: '50%' }} />;
  }
};

// Confetti burst for celebrations
export const Confetti: React.FC<{ 
  trigger: boolean; 
  duration?: number;
  particleCount?: number;
  colors?: string[];
}> = ({ trigger, duration = 2000, particleCount = 50, colors = CELEBRATION_COLORS }) => {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (!trigger) return;
    
    setParticles(Array.from({ length: particleCount }, (_, i) => createParticle(i, colors)));
    
    const timer = setTimeout(() => setParticles([]), duration);
    return () => clearTimeout(timer);
  }, [trigger, particleCount, colors, duration]);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-50">
      <AnimatePresence>
        {particles.map((p) => (
          <motion.div
            key={p.id}
            initial={{ 
              x: `${p.x}vw`, 
              y: `${p.y}vh`, 
              rotate: p.rotation,
              scale: 1,
              opacity: 1 
            }}
            animate={{ 
              x: `${p.x + p.velocity.x * 10}vw`,
              y: `${p.y + 100}vh`,
              rotate: p.rotation + 720,
              scale: 0,
              opacity: 0 
            }}
            exit={{ opacity: 0 }}
            transition={{ duration: duration / 1000, ease: 'easeOut' }}
            className="absolute"
          >
            <ParticleShape shape={p.shape} size={p.size} color={p.color} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

// Success burst - green particles radiating from center
export const SuccessBurst: React.FC<{ trigger: boolean }> = ({ trigger }) => (
  <Confetti trigger={trigger} particleCount={30} colors={SUCCESS_COLORS} duration={1500} />
);

// XP gain animation
export const XPGain: React.FC<{ 
  amount: number; 
  show: boolean;
  onComplete?: () => void;
}> = ({ amount, show, onComplete }) => (
  <AnimatePresence onExitComplete={onComplete}>
    {show && (
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.8 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -30, scale: 1.2 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        className="fixed top-1/3 left-1/2 -translate-x-1/2 z-50"
      >
        <div className="bg-gradient-to-r from-yellow-400 to-amber-500 text-white font-black text-3xl px-6 py-3 rounded-2xl shadow-2xl flex items-center gap-2">
          <motion.div
            animate={{ rotate: [0, -10, 10, -10, 0] }}
            transition={{ duration: 0.5 }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l2.4 7.4h7.6l-6 4.6 2.3 7-6.3-4.6-6.3 4.6 2.3-7-6-4.6h7.6z" />
            </svg>
          </motion.div>
          +{amount} XP
        </div>
      </motion.div>
    )}
  </AnimatePresence>
);

// Streak flame - animated fire effect (no emoji)
export const StreakFlame: React.FC<{ days: number; animated?: boolean }> = ({ days, animated = true }) => (
  <div className="relative">
    <motion.svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      className={clsx(days > 0 ? 'text-orange-500' : 'text-gray-300')}
      animate={animated && days > 0 ? { scale: [1, 1.1, 1] } : {}}
      transition={{ duration: 1.5, repeat: Infinity }}
    >
      <path
        fill="currentColor"
        d="M12 23c-4.97 0-9-3.58-9-8 0-3.07 1.64-5.64 4-7.17V6c0-.55.45-1 1-1s1 .45 1 1v.83c.63-.38 1.3-.68 2-.88V4c0-.55.45-1 1-1s1 .45 1 1v1.05c.34.03.67.08 1 .15V4c0-.55.45-1 1-1s1 .45 1 1v2c2.36 1.53 4 4.1 4 7.17 0 4.42-4.03 8-9 8z"
      />
      {days > 0 && (
        <motion.path
          fill="#FDE047"
          d="M12 17c-2.21 0-4-1.79-4-4 0-1.66.81-3.13 2.06-4.04l.94.7c-.63.67-1 1.58-1 2.59 0 1.1.9 2 2 2s2-.9 2-2c0-1.01-.37-1.92-1-2.59l.94-.7C15.19 9.87 16 11.34 16 13c0 2.21-1.79 4-4 4z"
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
    </motion.svg>
  </div>
);

// Heart icon with animation
export const Heart: React.FC<{ filled: boolean; breaking?: boolean }> = ({ filled, breaking }) => (
  <motion.svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    animate={breaking ? { scale: [1, 1.3, 0.8, 1], rotate: [0, -10, 10, 0] } : {}}
    transition={{ duration: 0.4 }}
  >
    <path
      fill={filled ? '#ff4b4b' : '#e5e7eb'}
      d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
    />
  </motion.svg>
);

// Crown for mastery
export const Crown: React.FC<{ size?: number; color?: string }> = ({ size = 24, color = '#ffc800' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .55-.45 1-1 1H6c-.55 0-1-.45-1-1v-1h14v1z" />
  </svg>
);

// Progress ring with animation
export const ProgressRing: React.FC<{
  progress: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  bgColor?: string;
  children?: React.ReactNode;
}> = ({ progress, size = 60, strokeWidth = 5, color = '#58cc02', bgColor = '#e5e7eb', children }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (Math.min(progress, 100) / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={bgColor} strokeWidth={strokeWidth} fill="none" />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{ strokeDasharray: circumference }}
        />
      </svg>
      {children && (
        <div className="absolute inset-0 flex items-center justify-center">
          {children}
        </div>
      )}
    </div>
  );
};

// Module completion celebration
export const ModuleComplete: React.FC<{ 
  show: boolean; 
  moduleNumber: number;
  onContinue: () => void;
}> = ({ show, moduleNumber, onContinue }) => (
  <AnimatePresence>
    {show && (
      <>
        <SuccessBurst trigger={show} />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-40"
        >
          <motion.div
            initial={{ scale: 0.8, y: 50 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.8, y: 50 }}
            className="bg-white rounded-3xl p-8 text-center max-w-sm mx-4 shadow-2xl"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', delay: 0.2 }}
              className="w-20 h-20 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4"
            >
              <svg width="40" height="40" viewBox="0 0 24 24" fill="white">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
              </svg>
            </motion.div>
            
            <h2 className="text-2xl font-black text-gray-900 mb-2">Module {moduleNumber} Complete!</h2>
            <p className="text-gray-500 mb-6">Great progress! Ready for the next challenge?</p>
            
            <button
              onClick={onContinue}
              className="w-full bg-[#58cc02] text-white font-bold py-4 rounded-2xl hover:bg-[#4db302] transition-colors shadow-lg"
            >
              Continue
            </button>
          </motion.div>
        </motion.div>
      </>
    )}
  </AnimatePresence>
);

// Mascot character (Playful Fox - distinct from the green owl)
export const Mascot: React.FC<{ 
  mood?: 'happy' | 'thinking' | 'celebrating' | 'encouraging';
  size?: number;
}> = ({ mood = 'happy', size = 80 }) => {
  const isExcited = mood === 'celebrating' || mood === 'encouraging';
  const isThinking = mood === 'thinking';
  const eyeY = isExcited ? 24 : isThinking ? 20 : 22;

  return (
    <motion.svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      animate={mood === 'celebrating' ? { y: [0, -5, 0] } : {}}
      transition={{ duration: 0.5, repeat: mood === 'celebrating' ? Infinity : 0 }}
    >
      {/* Ears */}
      <path d="M10 8L18 18L6 20Z" fill="#e65100" />
      <path d="M38 8L30 18L42 20Z" fill="#e65100" />
      
      {/* Head & Face Mask */}
      <path d="M24 44C36 44 44 36 44 26C44 14 36 8 24 8C12 8 4 14 4 26C4 36 12 44 24 44Z" fill="#ff9800" />
      <path d="M24 44C32 44 38 38 38 30C38 24 32 24 24 30C16 24 10 24 10 30C10 38 16 44 24 44Z" fill="#fff" />
      
      {/* Eyes & Nose */}
      <g fill="#1a1a1a">
        <circle cx="17" cy={eyeY} r="3" />
        <circle cx="31" cy={eyeY} r="3" />
        <ellipse cx="24" cy="34" rx="3" ry="2" />
      </g>
      
      {/* Eye Shine */}
      <g fill="#fff">
        <circle cx="18" cy={eyeY - 1} r="1" />
        <circle cx="32" cy={eyeY - 1} r="1" />
      </g>

      {/* Mouth/Expression */}
      {isExcited && <path d="M22 38Q24 41 26 38" stroke="#1a1a1a" strokeWidth="1.5" fill="none" />}
      
      {/* Blush */}
      {!isThinking && (
        <g fill="#ff9999" opacity="0.5">
          <ellipse cx="12" cy="32" rx="3" ry="1.5" />
          <ellipse cx="36" cy="32" rx="3" ry="1.5" />
        </g>
      )}
    </motion.svg>
  );
};

export default {
  Confetti,
  SuccessBurst,
  XPGain,
  StreakFlame,
  Heart,
  Crown,
  ProgressRing,
  ModuleComplete,
  Mascot,
};
