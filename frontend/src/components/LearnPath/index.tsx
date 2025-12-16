import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Target, Award, RefreshCw, Sparkles, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { StreakFlame, Mascot, ProgressRing, Crown } from '../Celebrations';
import { UnitView, LevelNode } from './UnitCard';
import { MilestoneModal } from './MilestoneModal';
import { useComponentLogger } from '../../lib/logger';
import { microcopy } from '../../lib/microcopy';
import {
  getLearningPath,
  initializeProgress,
  findNextNode,
  CurriculumSection,
  CurriculumNode,
} from '../../services/curriculum';

interface Unit {
  id: string;
  number: number;
  title: string;
  description: string;
  nodes: LevelNode[];
  isCurrent: boolean;
  isLocked: boolean;
  isComplete: boolean;
}

interface UserProgress {
  streak: number;
  dailyGoal: number;
  dailyProgress: number;
  totalXp: number;
  crowns: number;
}

const transformNode = (node: CurriculumNode): LevelNode => ({
  id: node.id,
  title: node.title,
  level: node.level,
  level_type: node.level_type,
  status: node.status,
  total_reviews: node.total_reviews,
});

const transformApiData = (apiSections: CurriculumSection[]): Unit[] => {
  const units: Unit[] = [];
  let unitNum = 1;
  
  for (const section of apiSections) {
    for (const unit of section.units) {
      const nodes = unit.nodes.map(transformNode);
      const completedCount = nodes.filter(n => n.status === 'completed').length;
      
      units.push({
        id: unit.id,
        number: unitNum++,
        title: unit.title,
        description: unit.description || section.title,
        nodes,
        isCurrent: unit.nodes.some(n => n.status === 'available' || n.status === 'in_progress') && unit.status !== 'locked',
        isLocked: unit.status === 'locked',
        isComplete: completedCount === nodes.length && nodes.length > 0,
      });
    }
  }
  return units;
};

// Unit card for selection view
const UnitSelectCard: React.FC<{
  unit: Unit;
  onClick: () => void;
}> = ({ unit, onClick }) => {
  const completedCount = unit.nodes.filter(n => n.status === 'completed').length;
  const progress = unit.nodes.length > 0 ? (completedCount / unit.nodes.length) * 100 : 0;
  const nextLesson = unit.nodes.find(n => n.status === 'available' || n.status === 'in_progress');

  const cardStyle = unit.isComplete
    ? "bg-gradient-to-br from-yellow-400 via-amber-400 to-orange-400 shadow-xl shadow-amber-200/50"
    : unit.isCurrent
    ? "bg-gradient-to-br from-emerald-500 via-green-500 to-teal-500 shadow-xl shadow-green-200/50"
    : unit.isLocked
    ? "bg-gray-100 opacity-60"
    : "bg-white border border-gray-200 shadow-sm hover:shadow-lg hover:border-gray-300";

  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={!unit.isLocked ? { scale: 1.02, y: -4 } : {}}
      whileTap={!unit.isLocked ? { scale: 0.98 } : {}}
      onClick={onClick}
      disabled={unit.isLocked}
      className={clsx(
        "w-full rounded-3xl p-5 text-left transition-all",
        cardStyle
      )}
    >
      <div className="flex items-center gap-4">
        {/* Unit badge */}
        <div className={clsx(
          "w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl shrink-0",
          unit.isComplete ? "bg-white/25 text-white" :
          unit.isCurrent ? "bg-white/25 text-white" :
          unit.isLocked ? "bg-gray-200 text-gray-400" :
          "bg-primary-100 text-primary-600"
        )}>
          {unit.isComplete ? <Crown size={32} color="white" /> : unit.number}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className={clsx(
            "text-xs font-bold uppercase tracking-wider mb-0.5",
            unit.isCurrent || unit.isComplete ? "text-white/70" : "text-gray-400"
          )}>
            Unit {unit.number} · {unit.nodes.length} lessons
          </p>
          <h3 className={clsx(
            "font-bold text-lg truncate",
            unit.isCurrent || unit.isComplete ? "text-white" :
            unit.isLocked ? "text-gray-400" : "text-gray-900"
          )}>
            {unit.title}
          </h3>
          {nextLesson && !unit.isComplete && (
            <p className={clsx(
              "text-sm truncate mt-0.5",
              unit.isCurrent ? "text-white/80" : "text-gray-500"
            )}>
              Next: {nextLesson.title}
            </p>
          )}
          {unit.isComplete && (
            <p className="text-sm text-white/80 mt-0.5">Mastered!</p>
          )}
        </div>

        {/* Progress & arrow */}
        <div className="flex items-center gap-3 shrink-0">
          {!unit.isLocked && (
            <ProgressRing
              progress={progress}
              size={48}
              strokeWidth={4}
              color={unit.isComplete || unit.isCurrent ? '#ffffff' : '#22c55e'}
              bgColor={unit.isCurrent || unit.isComplete ? 'rgba(255,255,255,0.2)' : '#e5e7eb'}
            >
              <span className={clsx(
                "text-xs font-bold",
                unit.isCurrent || unit.isComplete ? "text-white" : "text-gray-600"
              )}>
                {completedCount}/{unit.nodes.length}
              </span>
            </ProgressRing>
          )}
          
          <div className={clsx(
            "w-10 h-10 rounded-xl flex items-center justify-center",
            unit.isCurrent || unit.isComplete ? "bg-white/15" : "bg-gray-100"
          )}>
            <ChevronRight size={20} className={
              unit.isCurrent || unit.isComplete ? "text-white" :
              unit.isLocked ? "text-gray-300" : "text-gray-500"
            } />
          </div>
        </div>
      </div>

      {/* Current unit CTA */}
      {unit.isCurrent && nextLesson && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 bg-white/20 backdrop-blur-sm rounded-xl px-4 py-3 flex items-center justify-between"
        >
          <span className="text-white font-medium text-sm">Continue learning</span>
          <Sparkles size={18} className="text-white" />
        </motion.div>
      )}
    </motion.button>
  );
};

// Stats bar
const StatsBar: React.FC<{ progress: UserProgress }> = ({ progress }) => {
  const dailyPercent = Math.min((progress.dailyProgress / progress.dailyGoal) * 100, 100);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-4 bg-white rounded-2xl p-4 shadow-sm border border-gray-100"
    >
      <div className="flex items-center gap-2">
        <StreakFlame days={progress.streak} />
        <div>
          <p className="font-black text-gray-900 leading-tight">{progress.streak}</p>
          <p className="text-xs text-gray-400">Streak</p>
        </div>
      </div>
      
      <div className="w-px h-8 bg-gray-200" />
      
      <div className="flex items-center gap-2">
        <ProgressRing progress={dailyPercent} size={36} strokeWidth={3} color="#22c55e">
          <Target size={12} className="text-green-500" />
        </ProgressRing>
        <div>
          <p className="font-black text-gray-900 leading-tight">{progress.dailyProgress}/{progress.dailyGoal}</p>
          <p className="text-xs text-gray-400">Daily XP</p>
        </div>
      </div>
      
      <div className="w-px h-8 bg-gray-200" />
      
      <div className="flex items-center gap-2">
        <div className="w-9 h-9 rounded-lg bg-primary-100 flex items-center justify-center">
          <Award size={18} className="text-primary-600" />
        </div>
        <div>
          <p className="font-black text-gray-900 leading-tight">{progress.totalXp.toLocaleString()}</p>
          <p className="text-xs text-gray-400">Total XP</p>
        </div>
      </div>
    </motion.div>
  );
};

// Loading skeleton
const LoadingSkeleton: React.FC = () => (
  <div className="space-y-4">
    <div className="h-16 bg-gray-100 rounded-2xl animate-shimmer" />
    {[1, 2, 3].map(i => (
      <div key={i} className="h-28 bg-gray-100 rounded-3xl animate-shimmer" />
    ))}
  </div>
);

export const LearnPath: React.FC = () => {
  const { logger } = useComponentLogger('LearnPath');
  const navigate = useNavigate();

  const [units, setUnits] = useState<Unit[]>([]);
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeUnitId, setActiveUnitId] = useState<string | null>(null);
  const [milestoneModal, setMilestoneModal] = useState({
    isOpen: false, unitTitle: '', xpEarned: 0, patternsLearned: 0,
  });

  const activeUnit = useMemo(() => units.find(u => u.id === activeUnitId), [units, activeUnitId]);
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let apiSections = await getLearningPath('ru');

      if (apiSections.length === 0 || !findNextNode(apiSections)) {
        await initializeProgress('ru');
        apiSections = await getLearningPath('ru');
      }

      const transformed = transformApiData(apiSections);
      setUnits(transformed);

      // Calculate progress
      let completedNodes = 0, totalNodes = 0, crownedUnits = 0;
      for (const unit of transformed) {
        totalNodes += unit.nodes.length;
        completedNodes += unit.nodes.filter(n => n.status === 'completed').length;
        if (unit.isComplete) crownedUnits++;
      }

      setProgress({
        streak: 0,
        dailyGoal: 50,
        dailyProgress: completedNodes * 10,
        totalXp: completedNodes * 50 + crownedUnits * 100,
        crowns: crownedUnits,
      });

      logger.info('Learning path loaded', { unitCount: transformed.length });
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
    logger.info('Lesson clicked', { nodeId: node.id });
    navigate(`/lesson/${node.id}`);
  }, [logger, navigate]);

  const handleUnitComplete = useCallback(() => {
    // Find next unit
    const currentIdx = units.findIndex(u => u.id === activeUnitId);
    const nextUnit = units[currentIdx + 1];
    
    if (nextUnit && !nextUnit.isLocked) {
      setActiveUnitId(nextUnit.id);
    } else {
      setActiveUnitId(null);
    }
  }, [units, activeUnitId]);

  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-4">
        <Mascot mood="thinking" size={100} />
        <h2 className="text-xl font-bold text-gray-900 mt-4 mb-2">Something went wrong</h2>
        <p className="text-gray-500 mb-6 max-w-sm">{error}</p>
        <button
          onClick={loadData}
          className="flex items-center gap-2 bg-[#58cc02] text-white font-bold px-6 py-3 rounded-xl hover:bg-[#4db302] border-b-4 border-[#4db302] active:border-b-2 active:translate-y-[2px]"
        >
          <RefreshCw size={18} /> Try Again
        </button>
      </div>
    );
  }

  // Full screen unit view
  if (activeUnit) {
    return (
      <UnitView
        unit={activeUnit}
        onBack={() => setActiveUnitId(null)}
        onNodeClick={handleNodeClick}
        onComplete={handleUnitComplete}
      />
    );
  }

  // Unit selection view
  return (
    <div className="animate-in fade-in duration-500 pb-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between gap-4 mb-6"
      >
        <div className="flex items-center gap-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.1 }}
          >
            <Mascot mood="happy" size={56} />
          </motion.div>
          <div>
            <h1 className="text-2xl font-black text-gray-900">{greeting}!</h1>
            <p className="text-gray-500">{microcopy.continuePrompt()}</p>
          </div>
        </div>
      </motion.div>

      {/* Stats */}
      {progress && <StatsBar progress={progress} />}

      {/* Units */}
      <div className="mt-8 space-y-4">
        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider px-1">
          Your Journey
        </h2>
        
        {units.map((unit, idx) => (
          <motion.div
            key={unit.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <UnitSelectCard
              unit={unit}
              onClick={() => !unit.isLocked && setActiveUnitId(unit.id)}
            />
          </motion.div>
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
