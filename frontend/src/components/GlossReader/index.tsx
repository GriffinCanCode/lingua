import React, { useState, useEffect } from 'react';
import { glossingService, FullGlossedText, GlossedText } from '../../services/glossing';

export const GlossReader: React.FC = () => {
  const [texts, setTexts] = useState<GlossedText[]>([]);
  const [currentText, setCurrentText] = useState<FullGlossedText | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Display toggles
  const [showOriginal, setShowOriginal] = useState(true);
  const [showMorphemes, setShowMorphemes] = useState(true);
  const [showGlosses, setShowGlosses] = useState(true);
  const [showTranslation, setShowTranslation] = useState(true);

  useEffect(() => {
    loadTexts();
  }, []);

  const loadTexts = async () => {
    try {
      const data = await glossingService.listTexts();
      setTexts(data);
      
      // If texts exist, load the first one automatically for demo
      if (data.length > 0) {
        loadFullText(data[0].id);
      } else {
        // Create a dummy text for demonstration if none exist
        const demoText = {
            text: {
                id: 'demo',
                title: 'Demo Text',
                original_text: 'Я читаю книгу',
                language: 'ru',
                translation: 'I am reading a book',
                difficulty: 1
            },
            lines: [
                {
                    original: ['Я', 'читаю', 'книгу'],
                    morphemes: ['Я', 'чита-ю', 'книг-у'],
                    glosses: ['1SG', 'read-1SG.PRS', 'book-ACC.SG'],
                    translation: 'I am reading a book'
                }
            ]
        };
        setCurrentText(demoText);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadFullText = async (id: string) => {
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
    <div className="max-w-4xl mx-auto p-4">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold mb-2">Interlinear Gloss Reader</h2>
          <p className="text-gray-600 text-sm">Analyze texts morpheme-by-morpheme.</p>
        </div>
        
        <div className="flex gap-2 text-sm">
          <label className="flex items-center gap-1 cursor-pointer bg-white px-3 py-1 rounded border shadow-sm">
            <input type="checkbox" checked={showOriginal} onChange={e => setShowOriginal(e.target.checked)} />
            Original
          </label>
          <label className="flex items-center gap-1 cursor-pointer bg-white px-3 py-1 rounded border shadow-sm">
            <input type="checkbox" checked={showMorphemes} onChange={e => setShowMorphemes(e.target.checked)} />
            Morphemes
          </label>
          <label className="flex items-center gap-1 cursor-pointer bg-white px-3 py-1 rounded border shadow-sm">
            <input type="checkbox" checked={showGlosses} onChange={e => setShowGlosses(e.target.checked)} />
            Glosses
          </label>
          <label className="flex items-center gap-1 cursor-pointer bg-white px-3 py-1 rounded border shadow-sm">
            <input type="checkbox" checked={showTranslation} onChange={e => setShowTranslation(e.target.checked)} />
            Translation
          </label>
        </div>
      </div>

      {texts.length > 0 && (
        <div className="mb-8 flex gap-2 overflow-x-auto pb-2">
          {texts.map(text => (
            <button
              key={text.id}
              onClick={() => loadFullText(text.id)}
              className={`px-4 py-2 rounded-full whitespace-nowrap text-sm ${
                currentText?.text.id === text.id 
                  ? 'bg-primary-600 text-white shadow-md' 
                  : 'bg-white text-gray-700 hover:bg-gray-100 border'
              }`}
            >
              {text.title || text.original_text.slice(0, 20) + '...'}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : currentText ? (
        <div className="bg-white rounded-lg shadow-lg p-8 font-serif">
          {currentText.text.title && (
            <h1 className="text-2xl font-bold text-center mb-8">{currentText.text.title}</h1>
          )}
          
          <div className="space-y-8">
            {currentText.lines.map((line, i) => (
              <div key={i} className="interlinear-block">
                <div className="flex flex-wrap gap-x-6 gap-y-4 mb-4">
                  {line.original.map((word, wIdx) => (
                    <div key={wIdx} className="flex flex-col">
                      {showOriginal && (
                        <div className="text-lg font-medium text-gray-900 mb-1">{word}</div>
                      )}
                      {showMorphemes && (
                        <div className="text-sm text-primary-700 font-mono mb-1">{line.morphemes[wIdx]}</div>
                      )}
                      {showGlosses && (
                        <div className="text-xs text-gray-500 uppercase font-tracking-wider">{line.glosses[wIdx]}</div>
                      )}
                    </div>
                  ))}
                </div>
                {showTranslation && line.translation && (
                  <div className="text-gray-600 italic border-l-4 border-gray-200 pl-4 py-1">
                    {line.translation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500 bg-white rounded-lg border-dashed border-2 border-gray-200">
          Select a text to begin reading.
        </div>
      )}
    </div>
  );
};

