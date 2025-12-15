import { Link } from 'react-router-dom';
import { GitBranch, Book, Activity } from 'lucide-react';

export const ToolsDashboard = () => {
  const tools = [
    {
      to: '/tools/morphology',
      title: 'Morphology',
      description: 'Explore word forms and grammatical patterns.',
      icon: Book,
      color: 'bg-purple-100 text-purple-600',
    },
    {
      to: '/tools/etymology',
      title: 'Etymology',
      description: 'Discover word origins and historical connections.',
      icon: GitBranch,
      color: 'bg-amber-100 text-amber-600',
    },
    {
      to: '/tools/phonetics',
      title: 'Phonetics',
      description: 'Master pronunciation with real-time spectrograms.',
      icon: Activity,
      color: 'bg-emerald-100 text-emerald-600',
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Linguistic Tools</h2>
        <p className="text-gray-500 mt-2">Deep dive into language mechanics and analysis.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {tools.map((tool) => (
          <Link
            key={tool.to}
            to={tool.to}
            className="flex flex-col p-6 bg-white border border-gray-200 rounded-2xl hover:border-primary-500 hover:shadow-lg transition-all duration-200 group"
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${tool.color} transition-transform group-hover:scale-110`}>
              <tool.icon size={24} />
            </div>
            <h3 className="text-lg font-bold text-gray-900 group-hover:text-primary-600 transition-colors">
              {tool.title}
            </h3>
            <p className="text-gray-500 mt-2 text-sm leading-relaxed">
              {tool.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
};

