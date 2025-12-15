import React, { useState, useEffect } from 'react';
import { productionService, Prompt, AttemptResponse } from '../../services/production';
import { Send, AlertCircle, CheckCircle, Lightbulb } from 'lucide-react';

export const ProductionPractice: React.FC = () => {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [currentPrompt, setCurrentPrompt] = useState<Prompt | null>(null);
  const [userInput, setUserInput] = useState('');
  const [feedback, setFeedback] = useState<AttemptResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [hintLevel, setHintLevel] = useState(0);
  const [startTime, setStartTime] = useState<number>(0);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const data = await productionService.getPrompts();
      setPrompts(data);
      if (data.length > 0) {
        selectPrompt(data[0]);
      } else {
        // Fallback for demo if no prompts in DB
        const demoPrompt = {
            id: 'demo',
            prompt_type: 'translation',
            prompt_text: 'Translate: "I have a red car"',
            difficulty: 1,
            hints: ['Use the construction "У меня есть..."', 'Car is feminine in Russian (машина)', 'Adjective must agree with noun']
        };
        selectPrompt(demoPrompt);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const selectPrompt = (prompt: Prompt) => {
    setCurrentPrompt(prompt);
    setUserInput('');
    setFeedback(null);
    setHintLevel(0);
    setStartTime(Date.now());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || !currentPrompt) return;

    setLoading(true);
    const timeTaken = Math.round((Date.now() - startTime) / 1000);
    
    try {
        // If demo mode (id starts with demo), mock response
        if (currentPrompt.id.startsWith('demo')) {
            // Mock logic
            const isCorrect = userInput.toLowerCase().includes('у меня есть красная машина');
            const mockResponse: AttemptResponse = {
                id: 'mock-attempt',
                prompt_id: currentPrompt.id,
                user_response: userInput,
                is_correct: isCorrect ? 'Y' : 'N',
                score: isCorrect ? 1.0 : 0.4,
                feedback: {
                    is_correct: isCorrect ? 'Y' : 'N',
                    score: isCorrect ? 1.0 : 0.4,
                    errors: isCorrect ? [] : [
                        {
                            error_type: 'morphological',
                            description: 'Incorrect gender agreement',
                            correction: 'красная машина',
                            explanation: 'Машина is feminine, so the adjective must also be feminine.',
                            severity: 2
                        }
                    ],
                    corrected_text: 'У меня есть красная машина',
                    suggestions: isCorrect ? ['Great job!'] : ['Remember adjective-noun agreement rules.']
                }
            };
            setFeedback(mockResponse);
        } else {
            const response = await productionService.submitAttempt(
                currentPrompt.id, 
                userInput,
                timeTaken
            );
            setFeedback(response);
        }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const showNextHint = () => {
    if (currentPrompt && hintLevel < currentPrompt.hints.length) {
      setHintLevel(prev => prev + 1);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-6">Production Practice</h2>

      {currentPrompt ? (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="p-6 bg-primary-50 border-b border-primary-100">
            <span className="text-xs font-bold text-primary-600 uppercase tracking-wider">
              {currentPrompt.prompt_type.replace('_', ' ')}
            </span>
            <h3 className="text-xl font-medium mt-2">{currentPrompt.prompt_text}</h3>
          </div>

          <div className="p-6">
            {feedback ? (
              <div className="animate-fadeIn">
                <div className={`p-4 rounded-lg mb-6 flex items-start gap-3 ${
                  feedback.is_correct === 'Y' ? 'bg-green-50 text-green-800' : 
                  feedback.is_correct === 'P' ? 'bg-yellow-50 text-yellow-800' : 
                  'bg-red-50 text-red-800'
                }`}>
                  {feedback.is_correct === 'Y' ? <CheckCircle className="shrink-0" /> : <AlertCircle className="shrink-0" />}
                  <div>
                    <div className="font-bold text-lg mb-1">
                      {feedback.is_correct === 'Y' ? 'Correct!' : 
                       feedback.is_correct === 'P' ? 'Almost there!' : 'Not quite right'}
                    </div>
                    <p>{feedback.feedback.corrected_text}</p>
                  </div>
                </div>

                {feedback.feedback.errors.length > 0 && (
                  <div className="mb-6">
                    <h4 className="font-bold text-gray-700 mb-2">Analysis:</h4>
                    <div className="space-y-3">
                      {feedback.feedback.errors.map((error, i) => (
                        <div key={i} className="border-l-4 border-red-400 bg-gray-50 p-3">
                          <div className="text-sm text-red-600 font-bold uppercase">{error.error_type} error</div>
                          <div className="font-medium text-gray-900">{error.description}</div>
                          <div className="text-sm text-gray-600 mt-1">{error.explanation}</div>
                          <div className="mt-2 text-sm">
                            Try: <span className="font-mono bg-white px-1 rounded border">{error.correction}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => {
                    // Try to find next prompt
                    const currentIndex = prompts.findIndex(p => p.id === currentPrompt.id);
                    if (currentIndex < prompts.length - 1) {
                        selectPrompt(prompts[currentIndex + 1]);
                    } else {
                        // Reset to first
                        selectPrompt(prompts[0]);
                    }
                  }}
                  className="w-full bg-primary-600 text-white py-3 rounded-lg hover:bg-primary-700 transition"
                >
                  Next Challenge
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="mb-6">
                  <textarea
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    placeholder="Type your answer here..."
                    className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[120px] text-lg"
                    autoFocus
                  />
                </div>

                {hintLevel > 0 && (
                  <div className="mb-6 bg-yellow-50 p-4 rounded border border-yellow-100">
                    <h4 className="text-sm font-bold text-yellow-800 mb-2 flex items-center gap-2">
                      <Lightbulb size={16} /> Hints:
                    </h4>
                    <ul className="list-disc list-inside text-sm text-yellow-900">
                      {currentPrompt.hints.slice(0, hintLevel).map((hint, i) => (
                        <li key={i}>{hint}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex justify-between items-center">
                  <button
                    type="button"
                    onClick={showNextHint}
                    disabled={hintLevel >= currentPrompt.hints.length}
                    className="text-sm text-gray-500 hover:text-primary-600 disabled:opacity-50 flex items-center gap-1"
                  >
                    <Lightbulb size={16} />
                    {hintLevel === 0 ? 'Need a hint?' : 'Another hint?'}
                  </button>

                  <button
                    type="submit"
                    disabled={!userInput.trim() || loading}
                    className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {loading ? 'Analyzing...' : (
                      <>
                        Check Answer <Send size={16} />
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">Loading prompts...</div>
      )}
    </div>
  );
};

