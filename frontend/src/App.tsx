import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MorphologyViewer } from './components/MorphologyViewer';
import { EtymologyGraph } from './components/EtymologyGraph';
import { PhoneticsTrainer } from './components/Spectrogram';
import { SRSReview } from './components/SRSReview';
import { GlossReader } from './components/GlossReader';
import { ProductionPractice } from './components/ProductionPractice';
import { useNavigationLogger, useGlobalErrorLogger } from './lib/logger';
import { Layout } from './components/Layout';
import { ToolsDashboard } from './components/ToolsDashboard';

const AppContent = () => {
  useNavigationLogger();
  useGlobalErrorLogger();

  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Main Learning Flow */}
        <Route path="/" element={<SRSReview />} />
        
        {/* Core Activities */}
        <Route path="/practice" element={<ProductionPractice />} />
        <Route path="/reader" element={<GlossReader />} />
        
        {/* Tools Section */}
        <Route path="/tools" element={<ToolsDashboard />} />
        <Route path="/tools/morphology" element={<MorphologyViewer />} />
        <Route path="/tools/etymology" element={<EtymologyGraph />} />
        <Route path="/tools/phonetics" element={<PhoneticsTrainer />} />
        
        {/* Redirect Legacy Routes */}
        <Route path="/morphology" element={<Navigate to="/tools/morphology" replace />} />
        <Route path="/etymology" element={<Navigate to="/tools/etymology" replace />} />
        <Route path="/phonetics" element={<Navigate to="/tools/phonetics" replace />} />
        <Route path="/srs" element={<Navigate to="/" replace />} />
        <Route path="/glossing" element={<Navigate to="/reader" replace />} />
        <Route path="/production" element={<Navigate to="/practice" replace />} />
      </Route>
    </Routes>
  );
};

const App = () => (
  <Router>
    <AppContent />
  </Router>
);

export default App;
