import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Flame, Target, Award, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { SectionHeader } from './SectionHeader';
import { UnitCard, LevelNode } from './UnitCard';
import { MilestoneModal } from './MilestoneModal';
import { useComponentLogger } from '../../lib/logger';
import {
  getLearningPath,
  initializeProgress,
  findNextNode,
  CurriculumSection,
  CurriculumNode,
} from '../../services/curriculum';

interface Section {
  id: string;
  number: number;
  title: string;
  units: Unit[];
}

interface Unit {
  id: string;
  number: number;
  title: string;
  description: string;
  nodes: LevelNode[];
  isCurrent: boolean;
  isLocked: boolean;
}

interface UserProgress {
  streak: number;
  dailyGoal: number;
  dailyProgress: number;
  totalXp: number;
}

// Transform API node to LevelNode for UnitCard
const transformNode = (node: CurriculumNode): LevelNode => ({
  id: node.id,
  title: node.title,
  level: node.level,
  level_type: node.level_type,
  status: node.status,
  total_reviews: node.total_reviews,
});

// Transform API data to internal format
const transformApiData = (apiSections: CurriculumSection[]): Section[] =>
  apiSections.map((section, sIdx) => ({
    id: section.id,
    number: sIdx + 1,
    title: section.title,
    units: section.units.map((unit, uIdx) => ({
      id: unit.id,
      number: uIdx + 1,
      title: unit.title,
      description: unit.description || '',
      isCurrent: unit.nodes.some(n => n.status === 'available' || n.status === 'in_progress') && unit.status !== 'locked',
      isLocked: unit.status === 'locked',
      nodes: unit.nodes.map(transformNode),
    })),
  }));

export const LearnPath: React.FC = () => {
  const { logger } = useComponentLogger('LearnPath');
  const navigate = useNavigate();

  const [sections, setSections] = useState<Section[]>([]);
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [milestoneModal, setMilestoneModal] = useState({
    isOpen: false, unitTitle: '', xpEarned: 0, patternsLearned: 0,
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let apiSections = await getLearningPath('ru');

      // Initialize progress if no sections or all nodes are locked
      if (apiSections.length === 0 || !findNextNode(apiSections)) {
        await initializeProgress('ru');
        apiSections = await getLearningPath('ru');
      }

      setSections(transformApiData(apiSections));

      // Calculate progress
      let totalNodes = 0, completedNodes = 0, crownedUnits = 0;
      for (const section of apiSections) {
        for (const unit of section.units) {
          totalNodes += unit.total_nodes;
          completedNodes += unit.completed_nodes;
          if (unit.is_crowned) crownedUnits++;
        }
      }

      setProgress({
        streak: 0,
        dailyGoal: 50,
        dailyProgress: completedNodes * 10,
        totalXp: completedNodes * 50 + crownedUnits * 100,
      });

      logger.info('Learning path loaded', { sectionCount: apiSections.length });
    } catch (err) {
      logger.error('Failed to load learning path', err instanceof Error ? err : undefined);
      setError('Failed to load your learning path. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [logger]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleNodeClick = useCallback((node: LevelNode) => {
    if (node.status === 'locked') return;
    logger.info('Node clicked', { nodeId: node.id, level: node.level, type: node.level_type });
    navigate(`/lesson/${node.id}`);
  }, [logger, navigate]);

  const getUnitStats = (unit: Unit) => ({
    completed: unit.nodes.filter(n => n.status === 'completed').length,
    total: unit.nodes.length,
  });

  if (loading) {
    return (
      <div className="animate-in fade-in duration-300">
        <div className="h-20 bg-gray-100 rounded-2xl animate-pulse mb-8" />
        <div className="space-y-6">
          {[1, 2, 3].map(i => <div key={i} className="h-32 bg-gray-100 rounded-3xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mb-6">
          <span className="text-4xl">😵</span>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h2>
        <p className="text-gray-500 mb-6 max-w-sm">{error}</p>
        <button onClick={loadData} className="flex items-center gap-2 bg-primary-600 text-white font-bold px-6 py-3 rounded-xl hover:bg-primary-700">
          <RefreshCw size={18} /> Try Again
        </button>
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center mb-6 shadow-xl">
          <span className="text-5xl">🚀</span>
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Lingua!</h2>
        <p className="text-gray-500 mb-8 max-w-sm">Your personalized language learning path is being prepared.</p>
        <button onClick={() => navigate('/practice')} className="bg-green-500 text-white font-bold px-8 py-4 rounded-xl shadow-lg hover:bg-green-600">
          Start Your Journey
        </button>
      </div>
    );
  }

  const dailyProgressPercent = progress ? (progress.dailyProgress / progress.dailyGoal) * 100 : 0;

  return (
    <div className="animate-in fade-in duration-500">
      {/* Header Stats */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Your Path</h1>
          <p className="text-gray-500 mt-1">Continue where you left off</p>
        </div>

        {progress && (
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center", progress.streak > 0 ? "bg-orange-100" : "bg-gray-100")}>
                <Flame size={20} className={progress.streak > 0 ? "text-orange-500" : "text-gray-400"} />
              </div>
              <div>
                <p className="font-black text-gray-900">{progress.streak}</p>
                <p className="text-xs text-gray-400">Day Streak</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative w-10 h-10">
                <svg className="w-10 h-10 transform -rotate-90">
                  <circle cx="20" cy="20" r="16" fill="none" stroke="#e5e7eb" strokeWidth="4" />
                  <motion.circle cx="20" cy="20" r="16" fill="none" stroke="#22c55e" strokeWidth="4" strokeLinecap="round" strokeDasharray={100.53} initial={{ strokeDashoffset: 100.53 }} animate={{ strokeDashoffset: 100.53 * (1 - dailyProgressPercent / 100) }} />
                </svg>
                <Target size={14} className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-green-500" />
              </div>
              <div>
                <p className="font-black text-gray-900">{progress.dailyProgress}/{progress.dailyGoal}</p>
                <p className="text-xs text-gray-400">Daily XP</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center">
                <Award size={20} className="text-primary-600" />
              </div>
              <div>
                <p className="font-black text-gray-900">{progress.totalXp.toLocaleString()}</p>
                <p className="text-xs text-gray-400">Total XP</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Learning Path */}
      <div className="space-y-8">
        {sections.map(section => (
          <div key={section.id}>
            <SectionHeader
              sectionNumber={section.number}
              title={section.title}
              isSticky
              isComplete={section.units.every(u => u.nodes.every(n => n.status === 'completed'))}
            />
            <div className="space-y-4 mt-4">
              {section.units.map(unit => {
                const stats = getUnitStats(unit);
                return (
                  <UnitCard
                    key={unit.id}
                    id={unit.id}
                    title={unit.title}
                    description={unit.description}
                    unitNumber={unit.number}
                    nodes={unit.nodes}
                    isCurrent={unit.isCurrent}
                    isLocked={unit.isLocked}
                    isExpanded={unit.isCurrent}
                    completedCount={stats.completed}
                    totalCount={stats.total}
                    onNodeClick={handleNodeClick}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <MilestoneModal
        isOpen={milestoneModal.isOpen}
        onClose={() => setMilestoneModal(prev => ({ ...prev, isOpen: false }))}
        onContinue={() => setMilestoneModal(prev => ({ ...prev, isOpen: false }))}
        unitTitle={milestoneModal.unitTitle}
        xpEarned={milestoneModal.xpEarned}
        patternsLearned={milestoneModal.patternsLearned}
      />
    </div>
  );
};

export default LearnPath;
