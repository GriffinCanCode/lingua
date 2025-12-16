import { Link } from 'react-router-dom';
import { GitBranch, Book, Activity, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export const ToolsDashboard = () => {
  const tools = [
    {
      to: '/tools/morphology',
      title: 'Morphology Analyzer',
      description: 'Break down any Russian word into its components. See roots, prefixes, suffixes, and grammatical forms.',
      icon: Book,
      gradient: 'from-purple-500 to-indigo-600',
      bgLight: 'bg-purple-50',
      features: ['Word decomposition', 'Grammar patterns', 'Declension tables'],
    },
    {
      to: '/tools/etymology',
      title: 'Etymology Explorer',
      description: 'Discover word origins and trace linguistic connections across Slavic languages.',
      icon: GitBranch,
      gradient: 'from-amber-500 to-orange-600',
      bgLight: 'bg-amber-50',
      features: ['Word origins', 'Language family trees', 'Cognate finder'],
    },
    {
      to: '/tools/phonetics',
      title: 'Phonetics Lab',
      description: 'Master pronunciation with real-time spectrograms. Compare your speech to native speakers.',
      icon: Activity,
      gradient: 'from-emerald-500 to-teal-600',
      bgLight: 'bg-emerald-50',
      features: ['Spectrogram analysis', 'Pronunciation scoring', 'Accent training'],
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-extrabold text-gray-900">Linguistic Tools</h2>
        <p className="text-gray-500 mt-2">Advanced tools to deepen your understanding of Russian.</p>
      </div>

      {/* Tool Cards */}
      <div className="space-y-4">
        {tools.map((tool, idx) => (
          <motion.div
            key={tool.to}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
          >
            <Link
              to={tool.to}
              className="group block bg-white border border-gray-200 rounded-2xl overflow-hidden hover:border-gray-300 hover:shadow-lg transition-all duration-300"
            >
              <div className="flex items-stretch">
                {/* Icon Section */}
                <div className={`w-32 bg-gradient-to-br ${tool.gradient} flex items-center justify-center p-6`}>
                  <tool.icon size={40} className="text-white" />
                </div>

                {/* Content */}
                <div className="flex-1 p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900 group-hover:text-primary-600 transition-colors">
                        {tool.title}
                      </h3>
                      <p className="text-gray-500 mt-1 text-sm leading-relaxed max-w-lg">
                        {tool.description}
                      </p>
                    </div>
                    <ArrowRight size={20} className="text-gray-300 group-hover:text-primary-500 group-hover:translate-x-1 transition-all mt-1" />
                  </div>

                  {/* Features */}
                  <div className="flex flex-wrap gap-2 mt-4">
                    {tool.features.map(feature => (
                      <span key={feature} className={`px-3 py-1 ${tool.bgLight} text-gray-600 text-xs font-medium rounded-full`}>
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Quick Tips */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-6 border border-gray-200">
        <h3 className="font-bold text-gray-900 mb-3">💡 Pro Tips</h3>
        <ul className="space-y-2 text-sm text-gray-600">
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            Use the Morphology Analyzer when you encounter unfamiliar words in your reading.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            Etymology helps you remember words by understanding their roots and connections.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500 font-bold">•</span>
            Practice pronunciation early - it's easier to fix habits before they form!
          </li>
        </ul>
      </div>
    </div>
  );
};
