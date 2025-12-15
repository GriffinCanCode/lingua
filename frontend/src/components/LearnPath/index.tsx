import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Flame, Target, Award, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { SectionHeader } from './SectionHeader';
import { UnitCard } from './UnitCard';
import { MilestoneModal } from './MilestoneModal';
import { SkillNodeData, NodeState } from './SkillNode';
import { useComponentLogger, useTracedAsync } from '../../lib/logger';

// Mock data types - replace with actual service types
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
  nodes: SkillNodeData[];
  isCurrent: boolean;
  isLocked: boolean;
}

interface UserProgress {
  streak: number;
  dailyGoal: number;
  dailyProgress: number;
  totalXp: number;
}

// Icon mapping for node types
const getNodeIcon = (patternType: string) => {
  const icons: Record<string, React.ElementType> = {
    case: Award,
    tense: Flame,
    agreement: Target,
  };
  return icons[patternType] || Award;
};

// Generate mock learning path data
const generateMockData = (): { sections: Section[]; progress: UserProgress } => {
  const sections: Section[] = [
    {
      id: 'section-1',
      number: 1,
      title: 'Case Foundations',
      units: [
        {
          id: 'unit-1',
          number: 1,
          title: 'Nominative Case',
          description: 'Subject marking and basic sentence structure',
          isCurrent: false,
          isLocked: false,
          nodes: [
            { id: 'n1', title: 'Singular Nouns', icon: Award, state: 'completed' as NodeState, level: 5, maxLevel: 5, patternCount: 3, estimatedMinutes: 5 },
            { id: 'n2', title: 'Plural Nouns', icon: Award, state: 'completed' as NodeState, level: 5, maxLevel: 5, patternCount: 3, estimatedMinutes: 5 },
            { id: 'n3', title: 'Mixed Practice', icon: Target, state: 'crowned' as NodeState, level: 5, maxLevel: 5, patternCount: 6, estimatedMinutes: 8 },
          ],
        },
        {
          id: 'unit-2',
          number: 2,
          title: 'Accusative Case',
          description: 'Direct objects and motion verbs',
          isCurrent: true,
          isLocked: false,
          nodes: [
            { id: 'n4', title: 'Inanimate Objects', icon: Award, state: 'completed' as NodeState, level: 4, maxLevel: 5, patternCount: 4, estimatedMinutes: 5 },
            { id: 'n5', title: 'Animate Objects', icon: Award, state: 'current' as NodeState, level: 2, maxLevel: 5, patternCount: 4, estimatedMinutes: 6 },
            { id: 'n6', title: 'Motion Verbs', icon: Award, state: 'available' as NodeState, level: 0, maxLevel: 5, patternCount: 5, estimatedMinutes: 7 },
          ],
        },
        {
          id: 'unit-3',
          number: 3,
          title: 'Genitive Case',
          description: 'Possession and negation',
          isCurrent: false,
          isLocked: false,
          nodes: [
            { id: 'n7', title: 'Possession', icon: Award, state: 'needs_practice' as NodeState, level: 3, maxLevel: 5, patternCount: 4, estimatedMinutes: 5 },
            { id: 'n8', title: 'Negation', icon: Award, state: 'locked' as NodeState, level: 0, maxLevel: 5, patternCount: 3, estimatedMinutes: 5 },
            { id: 'n9', title: 'Quantities', icon: Award, state: 'locked' as NodeState, level: 0, maxLevel: 5, patternCount: 4, estimatedMinutes: 6 },
          ],
        },
      ],
    },
    {
      id: 'section-2',
      number: 2,
      title: 'Verbal System',
      units: [
        {
          id: 'unit-4',
          number: 4,
          title: 'Present Tense',
          description: 'Conjugation patterns for present actions',
          isCurrent: false,
          isLocked: true,
          nodes: [
            { id: 'n10', title: 'First Conjugation', icon: Flame, state: 'locked' as NodeState, level: 0, maxLevel: 5, patternCount: 5, estimatedMinutes: 7 },
            { id: 'n11', title: 'Second Conjugation', icon: Flame, state: 'locked' as NodeState, level: 0, maxLevel: 5, patternCount: 5, estimatedMinutes: 7 },
          ],
        },
        {
          id: 'unit-5',
          number: 5,
          title: 'Past Tense',
          description: 'Gender agreement and aspect introduction',
          isCurrent: false,
          isLocked: true,
          nodes: [
            { id: 'n12', title: 'Past Formation', icon: Flame, state: 'locked' as NodeState, level: 0, maxLevel: 5, patternCount: 4, estimatedMinutes: 6 },
          ],
        },
      ],
    },
  ];

  const progress: UserProgress = {
    streak: 7,
    dailyGoal: 50,
    dailyProgress: 30,
    totalXp: 1250,
  };

  return { sections, progress };
};

export const LearnPath: React.FC = () => {
  const { logger } = useComponentLogger('LearnPath');
  const traceAsync = useTracedAsync('learn');
  const navigate = useNavigate();

  const [sections, setSections] = useState<Section[]>([]);
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [milestoneModal, setMilestoneModal] = useState<{
    isOpen: boolean;
    unitTitle: string;
    xpEarned: number;
    patternsLearned: number;
  }>({ isOpen: false, unitTitle: '', xpEarned: 0, patternsLearned: 0 });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // TODO: Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network
      const { sections: s, progress: p } = generateMockData();
      setSections(s);
      setProgress(p);
      logger.info('Learning path loaded', { unitCount: s.reduce((a, s) => a + s.units.length, 0) });
    } catch (err) {
      logger.error('Failed to load learning path', err instanceof Error ? err : undefined);
      setError('Failed to load your learning path. Please try again.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleNodeClick = useCallback((node: SkillNodeData) => {
    logger.info('Node clicked', { nodeId: node.id, state: node.state });
    
    // Navigate to review session with this node's patterns
    // For now, just navigate to the SRS review (which is the root)
    navigate('/', { state: { nodeId: node.id } });
  }, [logger, navigate]);

  const getUnitStats = (unit: Unit) => {
    const completed = unit.nodes.filter(n => 
      n.state === 'completed' || n.state === 'crowned'
    ).length;
    return { completed, total: unit.nodes.length };
  };

  // Render loading state
  if (loading) {
    return (
      <div className="animate-in fade-in duration-300">
        {/* Skeleton header */}
        <div className="h-20 bg-gray-100 rounded-2xl animate-pulse mb-8" />
        
        {/* Skeleton units */}
        <div className="space-y-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-gray-100 rounded-3xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mb-6">
          <span className="text-4xl">😵</span>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h2>
        <p className="text-gray-500 mb-6 max-w-sm">{error}</p>
        <button
          onClick={loadData}
          className="flex items-center gap-2 bg-primary-600 text-white font-bold px-6 py-3 rounded-xl hover:bg-primary-700 transition-colors"
        >
          <RefreshCw size={18} />
          Try Again
        </button>
      </div>
    );
  }

  // Render empty state (new user)
  if (sections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', damping: 10 }}
          className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center mb-6 shadow-xl shadow-primary-200"
        >
          <span className="text-5xl">🚀</span>
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Lingua!</h2>
        <p className="text-gray-500 mb-8 max-w-sm">
          Your personalized language learning path is being prepared. Let's start with the basics!
        </p>
        <button
          onClick={() => navigate('/practice')}
          className="bg-green-500 text-white font-bold px-8 py-4 rounded-xl shadow-lg shadow-green-200 hover:bg-green-600 transition-all transform hover:scale-105"
        >
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
            {/* Streak */}
            <div className="flex items-center gap-2">
              <div className={clsx(
                "w-10 h-10 rounded-xl flex items-center justify-center",
                progress.streak > 0 ? "bg-orange-100" : "bg-gray-100"
              )}>
                <Flame size={20} className={progress.streak > 0 ? "text-orange-500" : "text-gray-400"} />
              </div>
              <div>
                <p className="font-black text-gray-900">{progress.streak}</p>
                <p className="text-xs text-gray-400">Day Streak</p>
              </div>
            </div>

            {/* Daily Goal */}
            <div className="flex items-center gap-2">
              <div className="relative w-10 h-10">
                <svg className="w-10 h-10 transform -rotate-90">
                  <circle
                    cx="20" cy="20" r="16"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="4"
                  />
                  <motion.circle
                    cx="20" cy="20" r="16"
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeDasharray={100.53}
                    initial={{ strokeDashoffset: 100.53 }}
                    animate={{ strokeDashoffset: 100.53 * (1 - dailyProgressPercent / 100) }}
                    transition={{ duration: 0.8 }}
                  />
                </svg>
                <Target size={14} className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-green-500" />
              </div>
              <div>
                <p className="font-black text-gray-900">{progress.dailyProgress}/{progress.dailyGoal}</p>
                <p className="text-xs text-gray-400">Daily XP</p>
              </div>
            </div>

            {/* Total XP */}
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
        {sections.map((section, sIdx) => (
          <div key={section.id}>
            <SectionHeader
              sectionNumber={section.number}
              title={section.title}
              isSticky
              isComplete={section.units.every(u => 
                u.nodes.every(n => n.state === 'completed' || n.state === 'crowned')
              )}
            />
            
            <div className="space-y-4 mt-4">
              {section.units.map((unit) => {
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

      {/* Milestone Modal */}
      <MilestoneModal
        isOpen={milestoneModal.isOpen}
        onClose={() => setMilestoneModal(prev => ({ ...prev, isOpen: false }))}
        onContinue={() => {
          setMilestoneModal(prev => ({ ...prev, isOpen: false }));
          // Navigate to next unit
        }}
        unitTitle={milestoneModal.unitTitle}
        xpEarned={milestoneModal.xpEarned}
        patternsLearned={milestoneModal.patternsLearned}
      />
    </div>
  );
};

export default LearnPath;

