import React, { useState, useEffect } from 'react';
import { productionService, Prompt, AttemptResponse } from '../../services/production';
import { Send, AlertCircle, CheckCircle, Lightbulb, ArrowRight, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

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
    const demoPrompt: Prompt = {
        id: 'demo',
        prompt_type: 'translation',
        prompt_text: 'Translate: "I have a red car"',
        difficulty: 1,
        hints: ['Use the construction "У меня есть..."', 'Car is feminine in Russian (машина)', 'Adjective must agree with noun']
    };

    try {
      const data = await productionService.getPrompts();
      setPrompts(data);
      if (data.length > 0) {
        selectPrompt(data[0]);
      } else {
        // Fallback for demo if no prompts in DB
        setPrompts([demoPrompt]);
        selectPrompt(demoPrompt);
      }
    } catch (err) {
      console.error(err);
      // Fallback for demo on error
      setPrompts([demoPrompt]);
      selectPrompt(demoPrompt);
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
            // Check for russian chars to decide if it's somewhat correct attempt logic (very basic mock)
            const isCorrect = userInput.toLowerCase().includes('красная машина'); 
            
            // Artificial delay
            await new Promise(resolve => setTimeout(resolve, 800));

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
                            description: 'Incorrect gender agreement or word choice',
                            correction: 'красная машина',
                            explanation: 'Ensure adjectives agree with nouns in gender, number, and case.',
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
    <div className="max-w-3xl mx-auto h-full flex flex-col justify-center">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-extrabold text-gray-900 flex justify-center items-center gap-3">
            <MessageSquare className="text-primary-500" />
            Production Practice
        </h2>
        <p className="text-gray-500 mt-2">Generate language output with real-time AI feedback.</p>
      </div>

      {currentPrompt ? (
        <AnimatePresence mode="wait">
          <motion.div 
            key={currentPrompt.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden"
          >
            {/* Prompt Header */}
            <div className="p-8 bg-gray-50 border-b border-gray-100 flex flex-col items-center text-center">
              <span className="inline-block px-3 py-1 rounded-full bg-primary-100 text-primary-700 text-xs font-bold uppercase tracking-wider mb-4">
                {currentPrompt.prompt_type.replace('_', ' ')}
              </span>
              <h3 className="text-2xl font-serif text-gray-800 leading-relaxed max-w-xl">
                {currentPrompt.prompt_text}
              </h3>
            </div>

            <div className="p-8">
              {feedback ? (
                <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="space-y-6"
                >
                  <div className={clsx(
                    "p-6 rounded-2xl flex items-start gap-4",
                    feedback.is_correct === 'Y' ? 'bg-green-50 text-green-900' : 
                    feedback.is_correct === 'P' ? 'bg-yellow-50 text-yellow-900' : 
                    'bg-red-50 text-red-900'
                  )}>
                    {feedback.is_correct === 'Y' ? <CheckCircle className="shrink-0 mt-1" size={28} /> : <AlertCircle className="shrink-0 mt-1" size={28} />}
                    <div className="flex-1">
                      <div className="font-bold text-xl mb-2">
                        {feedback.is_correct === 'Y' ? 'Excellent!' : 
                         feedback.is_correct === 'P' ? 'Almost there!' : 'Needs Improvement'}
                      </div>
                      <p className="text-lg opacity-90">{feedback.feedback.corrected_text}</p>
                    </div>
                  </div>

                  {feedback.feedback.errors.length > 0 && (
                    <div className="bg-gray-50 rounded-2xl p-6">
                      <h4 className="font-bold text-gray-900 mb-4 uppercase text-sm tracking-wide">Analysis</h4>
                      <div className="space-y-4">
                        {feedback.feedback.errors.map((error, i) => (
                          <div key={i} className="flex gap-4 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                            <div className="w-1 bg-red-400 rounded-full shrink-0" />
                            <div>
                                <div className="text-xs font-bold text-red-500 uppercase mb-1">{error.error_type}</div>
                                <div className="font-medium text-gray-900 mb-1">{error.description}</div>
                                <div className="text-gray-600 text-sm leading-relaxed">{error.explanation}</div>
                                <div className="mt-2 text-sm">
                                    <span className="text-gray-400 mr-2">Fix:</span>
                                    <span className="font-mono bg-green-50 text-green-700 px-2 py-1 rounded">{error.correction}</span>
                                </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={() => {
                      const currentIndex = prompts.findIndex(p => p.id === currentPrompt.id);
                      if (currentIndex < prompts.length - 1) {
                          selectPrompt(prompts[currentIndex + 1]);
                      } else {
                          // Loop or fetch more (for demo just reset)
                          selectPrompt(prompts[0]);
                      }
                    }}
                    className="w-full group bg-gray-900 text-white font-bold py-4 rounded-xl hover:bg-gray-800 transition-all flex justify-center items-center gap-2"
                  >
                    <span>Next Challenge</span>
                    <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                  </button>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="relative">
                    <textarea
                      value={userInput}
                      onChange={(e) => setUserInput(e.target.value)}
                      placeholder="Type your translation..."
                      className="w-full p-6 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-primary-100 focus:border-primary-500 transition-all min-h-[160px] text-xl resize-none"
                      autoFocus
                    />
                    <div className="absolute bottom-4 right-4 text-xs text-gray-400 font-medium uppercase tracking-wide">
                        Press Enter to Submit
                    </div>
                  </div>

                  <AnimatePresence>
                    {hintLevel > 0 && (
                        <motion.div 
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="bg-yellow-50 p-6 rounded-2xl border border-yellow-100 overflow-hidden"
                        >
                            <h4 className="text-sm font-bold text-yellow-800 mb-3 flex items-center gap-2">
                            <Lightbulb size={18} /> Helpful Hints
                            </h4>
                            <ul className="space-y-2">
                            {currentPrompt.hints.slice(0, hintLevel).map((hint, i) => (
                                <motion.li 
                                    key={i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="text-yellow-900 flex items-start gap-2 text-sm"
                                >
                                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-yellow-400 shrink-0" />
                                    <span>{hint}</span>
                                </motion.li>
                            ))}
                            </ul>
                        </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="flex justify-between items-center pt-2">
                    <button
                      type="button"
                      onClick={showNextHint}
                      disabled={hintLevel >= currentPrompt.hints.length}
                      className="text-gray-500 hover:text-primary-600 disabled:opacity-30 disabled:hover:text-gray-500 font-medium transition-colors flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-50"
                    >
                      <Lightbulb size={20} />
                      {hintLevel === 0 ? 'Need a hint?' : 'Show another hint'}
                    </button>

                    <button
                      type="submit"
                      disabled={!userInput.trim() || loading}
                      className="bg-primary-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-primary-700 disabled:opacity-70 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-200 flex items-center gap-3 transform active:scale-95"
                    >
                      {loading ? (
                          <>Analyzing...</>
                      ) : (
                        <>
                          Check Answer <Send size={18} />
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      ) : (
        <div className="flex justify-center items-center h-64">
             <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      )}
    </div>
  );
};
