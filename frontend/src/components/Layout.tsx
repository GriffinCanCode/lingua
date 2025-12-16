import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Home, BookOpen, Dumbbell, Wrench, Settings, Brain, Flame, Zap, Trophy } from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface UserStats {
  streak: number;
  dailyXp: number;
  dailyGoal: number;
  totalXp: number;
  heartsRemaining: number;
}

export const Layout = () => {
  const location = useLocation();
  const [stats] = useState<UserStats>({
    streak: 3,
    dailyXp: 35,
    dailyGoal: 50,
    totalXp: 1250,
    heartsRemaining: 5,
  });

  // Check if we're in a lesson (hide stats during lessons)
  const inLesson = location.pathname.startsWith('/lesson/');

  const navItems = [
    { to: '/', icon: Home, label: 'Learn', color: 'text-green-500' },
    { to: '/review', icon: Brain, label: 'Review', color: 'text-purple-500' },
    { to: '/practice', icon: Dumbbell, label: 'Practice', color: 'text-blue-500' },
    { to: '/reader', icon: BookOpen, label: 'Reader', color: 'text-amber-500' },
    { to: '/tools', icon: Wrench, label: 'Tools', color: 'text-gray-500' },
  ];

  const dailyProgress = Math.min(100, (stats.dailyXp / stats.dailyGoal) * 100);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col fixed inset-y-0 z-50">
        {/* Logo */}
        <div className="p-6 border-b border-gray-100">
          <h1 className="text-2xl font-extrabold text-primary-600 tracking-tight">Lingua</h1>
        </div>

        {/* Stats Bar */}
        {!inLesson && (
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            {/* Streak */}
            <div className="flex items-center gap-1.5">
              <Flame size={18} className={stats.streak > 0 ? "text-orange-500" : "text-gray-300"} />
              <span className={clsx("font-bold text-sm", stats.streak > 0 ? "text-orange-500" : "text-gray-400")}>
                {stats.streak}
              </span>
            </div>

            {/* Daily XP Progress */}
            <div className="flex items-center gap-1.5">
              <div className="relative w-6 h-6">
                <svg className="w-6 h-6 transform -rotate-90">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="#e5e7eb" strokeWidth="2" />
                  <motion.circle
                    cx="12" cy="12" r="10"
                    fill="none"
                    stroke={dailyProgress >= 100 ? "#22c55e" : "#fbbf24"}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeDasharray={62.83}
                    initial={{ strokeDashoffset: 62.83 }}
                    animate={{ strokeDashoffset: 62.83 * (1 - dailyProgress / 100) }}
                  />
                </svg>
                <Zap size={10} className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-yellow-500" />
              </div>
              <span className="font-bold text-sm text-gray-600">{stats.dailyXp}</span>
            </div>

            {/* Total XP */}
            <div className="flex items-center gap-1.5">
              <Trophy size={16} className="text-primary-500" />
              <span className="font-bold text-sm text-primary-600">{stats.totalXp.toLocaleString()}</span>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label, color }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-semibold',
                  isActive
                    ? 'bg-primary-50 text-primary-600 border-l-4 border-primary-500'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={20} className={isActive ? 'text-primary-600' : color} />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100">
          <button className="flex items-center gap-3 px-4 py-3 text-gray-500 hover:text-gray-900 w-full rounded-xl hover:bg-gray-50 transition-colors font-medium">
            <Settings size={20} />
            <span>Settings</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 overflow-auto min-h-screen">
        <div className={clsx(
          "mx-auto",
          inLesson ? "max-w-4xl p-4" : "max-w-5xl p-8"
        )}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};
