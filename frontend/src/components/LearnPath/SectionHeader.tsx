import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface SectionHeaderProps {
  sectionNumber: number;
  title: string;
  isSticky?: boolean;
  isComplete?: boolean;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  sectionNumber,
  title,
  isSticky = false,
  isComplete = false,
}) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    className={clsx(
      "py-4 px-6 -mx-4 rounded-xl transition-all",
      isSticky && "sticky top-0 z-10 backdrop-blur-lg bg-gray-50/80",
      isComplete && "text-primary-600"
    )}
  >
    <div className="flex items-center gap-4">
      <div className={clsx(
        "w-10 h-10 rounded-full flex items-center justify-center font-black text-sm",
        isComplete ? "bg-primary-100 text-primary-600" : "bg-gray-200 text-gray-600"
      )}>
        {sectionNumber}
      </div>
      <div>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Section {sectionNumber}</p>
        <h2 className={clsx(
          "text-xl font-bold",
          isComplete ? "text-primary-600" : "text-gray-900"
        )}>
          {title}
        </h2>
      </div>
    </div>
  </motion.div>
);

