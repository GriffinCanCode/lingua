import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { PatternTableContent } from '../../types/teaching';

interface PatternTableProps {
  content: PatternTableContent;
}

export const PatternTable: React.FC<PatternTableProps> = ({ content }) => {
  const { title, columns, rows, highlight = [] } = content;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <h3 className="text-lg font-bold text-gray-800 mb-4">{title}</h3>
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50">
              {columns.map((col, i) => (
                <th key={i} className="px-4 py-3 text-left font-semibold text-gray-600 border-b">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <motion.tr
                key={rowIdx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: rowIdx * 0.05 }}
                className={clsx(
                  "border-b border-gray-100 last:border-b-0",
                  highlight.includes(rowIdx) ? "bg-primary-50" : "bg-white hover:bg-gray-50"
                )}
              >
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className={clsx(
                      "px-4 py-3",
                      cellIdx === 0 && "font-bold text-primary-700 text-lg"
                    )}
                  >
                    {cell}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};
