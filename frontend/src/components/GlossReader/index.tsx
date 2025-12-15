import React, { useState, useEffect } from 'react';
import { glossingService, FullGlossedText, GlossedText } from '../../services/glossing';
import { Settings2, BookOpen, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export const GlossReader: React.FC = () => {
  const [texts, setTexts] = useState<GlossedText[]>([]);
  const [currentText, setCurrentText] = useState<FullGlossedText | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Display toggles
  const [showOriginal, setShowOriginal] = useState(true);
  const [showMorphemes, setShowMorphemes] = useState(true);
  const [showGlosses, setShowGlosses] = useState(true);
  const [showTranslation, setShowTranslation] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    loadTexts();
  }, []);

  const loadTexts = async () => {
    // Mock data for UI development
    const demoText: FullGlossedText = {
      text: {
          id: 'demo',
          title: 'The Great Gatsby (Excerpt)',
          original_text: 'In my younger and more vulnerable years',
          language: 'en',
          translation: 'En mis años más jóvenes y vulnerables',
          difficulty: 1
      },
      lines: [
          {
              original: ['In', 'my', 'younger', 'and', 'more', 'vulnerable', 'years'],
              morphemes: ['In', 'my', 'young-er', 'and', 'more', 'vulnerable', 'year-s'],
              glosses: ['PREP', 'POSS.1SG', 'adj-CMPR', 'CONJ', 'ADV', 'ADJ', 'n-PL'],
              translation: 'En mis años más jóvenes y vulnerables'
          }
      ]
    };

    try {
      const data = await glossingService.listTexts();
      setTexts(data);
      
      if (data.length > 0) {
        loadFullText(data[0].id);
      } else {
        // Fallback to demo text if list is empty
        setCurrentText(demoText);
        setTexts([demoText.text]);
      }
    } catch (err) {
      console.error("Failed to load texts, using demo data", err);
      // Fallback to demo text on error
      setCurrentText(demoText);
      setTexts([demoText.text]);
    }
  };

  const loadFullText = async (id: string) => {
    if (id === 'demo') return; // Already loaded

    setLoading(true);
    try {
      const data = await glossingService.getText(id);
      setCurrentText(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto h-full flex flex-col">
      {/* Header & Controls */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-3">
            <BookOpen className="text-primary-600" />
            Interlinear Reader
          </h1>
          <p className="text-gray-500 mt-1">Deconstruct texts morpheme by morpheme.</p>
        </div>
        
        <div className="relative">
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all",
              showSettings ? "bg-primary-100 text-primary-700" : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
            )}
          >
            <Settings2 size={18} />
            <span>View Options</span>
          </button>
          
          <AnimatePresence>
            {showSettings && (
              <motion.div 
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 p-4 z-10"
              >
                <div className="space-y-3">
                  <Toggle label="Original Text" checked={showOriginal} onChange={setShowOriginal} />
                  <Toggle label="Morphemes" checked={showMorphemes} onChange={setShowMorphemes} />
                  <Toggle label="Glosses" checked={showGlosses} onChange={setShowGlosses} />
                  <Toggle label="Translation" checked={showTranslation} onChange={setShowTranslation} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Text Selection */}
      <div className="mb-8 overflow-x-auto pb-4 scrollbar-hide">
        <div className="flex gap-3">
          {texts.map(text => (
            <button
              key={text.id}
              onClick={() => loadFullText(text.id)}
              className={clsx(
                "px-5 py-2.5 rounded-xl whitespace-nowrap text-sm font-bold transition-all border-2",
                currentText?.text.id === text.id 
                  ? "bg-primary-600 text-white border-primary-600 shadow-md transform scale-105" 
                  : "bg-white text-gray-600 border-gray-200 hover:border-primary-300 hover:text-primary-600"
              )}
            >
              {text.title || "Untitled Text"}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="flex-1 flex justify-center items-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : currentText ? (
        <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8 md:p-12 min-h-[500px]">
          {currentText.text.title && (
            <h2 className="text-3xl font-serif font-bold text-gray-900 mb-12 text-center border-b pb-8">
              {currentText.text.title}
            </h2>
          )}
          
          <div className="space-y-12 max-w-3xl mx-auto">
            {currentText.lines.map((line, i) => (
              <div key={i} className="group">
                <div className="flex flex-wrap gap-x-6 gap-y-6 mb-4">
                  {line.original.map((word, wIdx) => (
                    <div key={wIdx} className="flex flex-col items-center hover:bg-gray-50 rounded px-1 -mx-1 transition-colors">
                      {showOriginal && (
                        <span className="text-xl font-medium text-gray-900 mb-1">{word}</span>
                      )}
                      {showMorphemes && (
                        <span className="text-sm text-primary-600 font-mono tracking-tight mb-0.5">{line.morphemes[wIdx]}</span>
                      )}
                      {showGlosses && (
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{line.glosses[wIdx]}</span>
                      )}
                    </div>
                  ))}
                </div>
                {showTranslation && line.translation && (
                  <div className="relative pl-6 mt-4">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary-200 rounded-full" />
                    <p className="text-lg text-gray-600 italic leading-relaxed">
                      {line.translation}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-center items-center text-gray-400 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200">
          <Layers size={48} className="mb-4 opacity-50" />
          <p>Select a text to start reading</p>
        </div>
      )}
    </div>
  );
};

const Toggle: React.FC<{ label: string; checked: boolean; onChange: (checked: boolean) => void }> = ({ label, checked, onChange }) => (
  <label className="flex items-center justify-between cursor-pointer group">
    <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">{label}</span>
    <div 
      className={clsx(
        "w-11 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out",
        checked ? "bg-primary-600" : "bg-gray-200"
      )}
      onClick={(e) => {
        e.preventDefault();
        onChange(!checked);
      }}
    >
      <div 
        className={clsx(
          "w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform duration-200 ease-in-out",
          checked ? "translate-x-5" : "translate-x-0"
        )}
      />
    </div>
  </label>
);
