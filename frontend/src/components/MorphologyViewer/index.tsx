import React, { useState } from 'react';
import { morphologyService, Paradigm } from '../../services/morphology';

const CASES = ['nominative', 'genitive', 'dative', 'accusative', 'instrumental', 'prepositional'];

export const MorphologyViewer: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [paradigm, setParadigm] = useState<Paradigm | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError('');
    try {
      const result = await morphologyService.getParadigm(searchTerm.trim());
      setParadigm(result);
    } catch (err) {
      setError('Failed to fetch paradigm. Word might not be found.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getForm = (caseName: string, number: string): string => {
    if (!paradigm) return '-';
    const forms = paradigm.inflections.filter(
      (i) => i.case === caseName && i.number === number
    );
    return forms.length > 0 ? forms[0].form : '-';
  };

  const highlightEnding = (word: string, lemma: string) => {
    // Simple logic to highlight ending
    // Real implementation would use data from backend about stemming
    if (!word || word === '-') return word;
    
    // Naive stemming for visualization
    let stem = lemma;
    if (lemma.endsWith('ь') || lemma.endsWith('й') || lemma.endsWith('а') || lemma.endsWith('я') || lemma.endsWith('о') || lemma.endsWith('е')) {
        stem = lemma.slice(0, -1);
    }
    
    if (word.startsWith(stem)) {
        const ending = word.slice(stem.length);
        return (
            <span>
                {stem}
                <span className="text-primary-600 font-bold">{ending}</span>
            </span>
        );
    }
    return word;
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Morphological Pattern Explorer</h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Enter a Russian word (e.g., город, мама)..."
            className="flex-1 p-2 border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-primary-600 text-white px-6 py-2 rounded hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </form>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>

      {paradigm && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="mb-6">
            <h3 className="text-xl font-bold">{paradigm.lemma.word}</h3>
            <p className="text-gray-600">
              {paradigm.lemma.part_of_speech} • {paradigm.lemma.gender || ''}
            </p>
          </div>

          {paradigm.lemma.part_of_speech === 'noun' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Case</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Singular</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plural</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {CASES.map((caseName) => (
                    <tr key={caseName}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 capitalize">
                        {caseName}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {highlightEnding(getForm(caseName, 'singular'), paradigm.lemma.word)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {highlightEnding(getForm(caseName, 'plural'), paradigm.lemma.word)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {paradigm.lemma.part_of_speech !== 'noun' && (
             <div className="text-center p-8 text-gray-500">
                Visualization for {paradigm.lemma.part_of_speech}s coming soon.
                <div className="mt-4 grid grid-cols-2 gap-4 text-left">
                    {paradigm.inflections.map((inf, i) => (
                        <div key={i} className="bg-gray-50 p-2 rounded">
                            <span className="font-bold">{inf.form}</span>
                            <span className="text-xs text-gray-500 ml-2 block">
                                {[inf.tense, inf.person, inf.number, inf.gender].filter(Boolean).join(', ')}
                            </span>
                        </div>
                    ))}
                </div>
             </div>
          )}
        </div>
      )}
    </div>
  );
};

