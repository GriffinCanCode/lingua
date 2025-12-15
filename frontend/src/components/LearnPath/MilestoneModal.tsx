import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Star, X, ArrowRight } from 'lucide-react';
import confetti from 'canvas-confetti';

interface MilestoneModalProps {
  isOpen: boolean;
  onClose: () => void;
  onContinue: () => void;
  unitTitle: string;
  xpEarned: number;
  patternsLearned: number;
}

export const MilestoneModal: React.FC<MilestoneModalProps> = ({
  isOpen,
  onClose,
  onContinue,
  unitTitle,
  xpEarned,
  patternsLearned,
}) => {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    if (isOpen && !showConfetti) {
      setShowConfetti(true);
      // Fire confetti
      const duration = 2000;
      const end = Date.now() + duration;
      
      const frame = () => {
        confetti({
          particleCount: 3,
          angle: 60,
          spread: 55,
          origin: { x: 0, y: 0.7 },
          colors: ['#0ea5e9', '#22c55e', '#f59e0b'],
        });
        confetti({
          particleCount: 3,
          angle: 120,
          spread: 55,
          origin: { x: 1, y: 0.7 },
          colors: ['#0ea5e9', '#22c55e', '#f59e0b'],
        });

        if (Date.now() < end) requestAnimationFrame(frame);
      };
      
      frame();
    }
    
    if (!isOpen) setShowConfetti(false);
  }, [isOpen, showConfetti]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.8, opacity: 0, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-3xl shadow-2xl max-w-md w-full overflow-hidden"
          >
            {/* Header */}
            <div className="bg-gradient-to-br from-amber-400 to-orange-500 p-8 text-center relative">
              <button
                onClick={onClose}
                className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white hover:bg-white/30 transition-colors"
              >
                <X size={18} />
              </button>
              
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.2, type: 'spring', damping: 10 }}
                className="w-24 h-24 mx-auto mb-4 bg-white rounded-full flex items-center justify-center shadow-xl"
              >
                <Trophy size={48} className="text-amber-500" />
              </motion.div>
              
              <motion.h2
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-2xl font-black text-white mb-1"
              >
                Unit Complete!
              </motion.h2>
              <p className="text-white/80 font-medium">{unitTitle}</p>
            </div>

            {/* Stats */}
            <div className="p-8">
              <div className="flex justify-center gap-8 mb-8">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="text-center"
                >
                  <div className="w-16 h-16 rounded-2xl bg-primary-100 flex items-center justify-center mx-auto mb-2">
                    <Star size={28} className="text-primary-600 fill-primary-600" />
                  </div>
                  <p className="text-2xl font-black text-gray-900">+{xpEarned}</p>
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">XP Earned</p>
                </motion.div>
                
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="text-center"
                >
                  <div className="w-16 h-16 rounded-2xl bg-green-100 flex items-center justify-center mx-auto mb-2">
                    <span className="text-2xl">📚</span>
                  </div>
                  <p className="text-2xl font-black text-gray-900">{patternsLearned}</p>
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Patterns</p>
                </motion.div>
              </div>

              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                onClick={onContinue}
                className="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-green-200 transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
              >
                Continue Learning
                <ArrowRight size={20} />
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

