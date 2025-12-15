import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { MorphologyViewer } from './components/MorphologyViewer';
import { EtymologyGraph } from './components/EtymologyGraph';
import { PhoneticsTrainer } from './components/Spectrogram';
import { SRSReview } from './components/SRSReview';
import { GlossReader } from './components/GlossReader';
import { ProductionPractice } from './components/ProductionPractice';
import { useNavigationLogger, useGlobalErrorLogger } from './lib/logger';

const AppContent = () => {
  // Setup navigation and global error logging
  useNavigationLogger();
  useGlobalErrorLogger();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">
            <Link to="/">Lingua</Link>
          </h1>
          <nav className="flex gap-4">
            <Link to="/morphology" className="text-gray-600 hover:text-primary-600">Morphology</Link>
            <Link to="/etymology" className="text-gray-600 hover:text-primary-600">Etymology</Link>
            <Link to="/phonetics" className="text-gray-600 hover:text-primary-600">Phonetics</Link>
            <Link to="/srs" className="text-gray-600 hover:text-primary-600">SRS</Link>
            <Link to="/glossing" className="text-gray-600 hover:text-primary-600">Reader</Link>
            <Link to="/production" className="text-gray-600 hover:text-primary-600">Practice</Link>
          </nav>
        </div>
      </header>
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={
              <div className="px-4 py-6 sm:px-0">
                <div className="border-4 border-dashed border-gray-200 rounded-lg p-12 text-center">
                  <h2 className="text-2xl font-bold text-gray-700 mb-4">Welcome to Lingua</h2>
                  <p className="text-gray-500 max-w-lg mx-auto mb-8">
                    An advanced language learning platform focusing on morphological patterns, etymology, and phonetics.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-4xl mx-auto">
                    <Link to="/morphology" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">Morphology</h3>
                      <p className="text-sm text-gray-500">Explore word forms and grammatical patterns.</p>
                    </Link>
                    <Link to="/etymology" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">Etymology</h3>
                      <p className="text-sm text-gray-500">Discover word origins and connections.</p>
                    </Link>
                    <Link to="/phonetics" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">Phonetics</h3>
                      <p className="text-sm text-gray-500">Master pronunciation with spectrograms.</p>
                    </Link>
                    <Link to="/srs" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">SRS Review</h3>
                      <p className="text-sm text-gray-500">Sentence-level spaced repetition.</p>
                    </Link>
                    <Link to="/glossing" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">Gloss Reader</h3>
                      <p className="text-sm text-gray-500">Read with interlinear breakdowns.</p>
                    </Link>
                    <Link to="/production" className="bg-white p-6 rounded shadow hover:shadow-md transition">
                      <h3 className="text-lg font-bold text-primary-600 mb-2">Production</h3>
                      <p className="text-sm text-gray-500">Practice output with targeted feedback.</p>
                    </Link>
                  </div>
                </div>
              </div>
            } />
            <Route path="/morphology" element={<MorphologyViewer />} />
            <Route path="/etymology" element={<EtymologyGraph />} />
            <Route path="/phonetics" element={<PhoneticsTrainer />} />
            <Route path="/srs" element={<SRSReview />} />
            <Route path="/glossing" element={<GlossReader />} />
            <Route path="/production" element={<ProductionPractice />} />
          </Routes>
        </div>
      </main>
    </div>
  );
};

const App = () => (
  <Router>
    <AppContent />
  </Router>
);

export default App;
