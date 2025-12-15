import { NavLink, Outlet } from 'react-router-dom';
import { Home, BookOpen, Dumbbell, Wrench, Settings, Brain } from 'lucide-react';
import clsx from 'clsx';

export const Layout = () => {
  const navItems = [
    { to: '/', icon: Home, label: 'Learn' },
    { to: '/review', icon: Brain, label: 'Review' },
    { to: '/practice', icon: Dumbbell, label: 'Practice' },
    { to: '/reader', icon: BookOpen, label: 'Reader' },
    { to: '/tools', icon: Wrench, label: 'Tools' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col fixed inset-y-0 z-50">
        <div className="p-6">
          <h1 className="text-2xl font-extrabold text-primary-600 tracking-tight">Lingua</h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium',
                  isActive
                    ? 'bg-primary-50 text-primary-600'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-100">
           <button className="flex items-center gap-3 px-4 py-3 text-gray-500 hover:text-gray-900 w-full rounded-xl hover:bg-gray-50 transition-colors font-medium">
             <Settings size={20} />
             <span>Settings</span>
           </button>
        </div>
      </aside>

      <main className="flex-1 ml-64 overflow-auto min-h-screen">
        <div className="max-w-5xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

