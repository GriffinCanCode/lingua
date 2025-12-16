import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import { Crown } from '../Celebrations';

interface SectionHeaderProps {
  sectionNumber: number;
  title: string;
  isComplete?: boolean;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  sectionNumber,
  title,
  isComplete = false,
}) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    className="py-4 px-5 -mx-2 rounded-2xl"
  >
    <div className="flex items-center gap-4">
      <motion.div
        whileHover={{ scale: 1.05 }}
        className={clsx(
          "w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg",
          isComplete
            ? "bg-gradient-to-br from-yellow-400 to-amber-500 text-white shadow-lg"
            : "bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-md"
        )}
      >
        {isComplete ? <Crown size={24} color="white" /> : sectionNumber}
      </motion.div>

      <div>
        <div className="flex items-center gap-2">
          <p className={clsx(
            "text-xs font-bold uppercase tracking-wider",
            isComplete ? "text-amber-600" : "text-gray-400"
          )}>
            Section {sectionNumber}
          </p>
          {isComplete && <CheckCircle2 size={14} className="text-amber-500" fill="#fef3c7" />}
        </div>
        <h2 className={clsx(
          "text-xl font-black tracking-tight",
          isComplete ? "text-amber-700" : "text-gray-900"
        )}>
          {title}
        </h2>
      </div>
    </div>
  </motion.div>
);
