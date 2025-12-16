import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, ChevronRight, Check, Lightbulb } from 'lucide-react';
import clsx from 'clsx';
import type { MorphPattern, GrammaticalCase, GrammarConfig, CaseConfig } from '../../types/exercises';

interface PatternExample {
  word: string;
  translation: string;
  stem: string;
  forms: { case: GrammaticalCase; form: string; ending: string }[];
}

interface PatternIntroProps {
  pattern: MorphPattern;
  examples: PatternExample[];
  onComplete: () => void;
  grammarConfig?: GrammarConfig;
}

// Fallback case config when API data not available
const DEFAULT_CASES: Record<GrammaticalCase, CaseConfig> = {
  nominative: { id: 'nominative', label: 'Nominative (кто? что?)', hint: '', color: { bg: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-300' } },
  genitive: { id: 'genitive', label: 'Genitive (кого? чего?)', hint: '', color: { bg: 'bg-green-100', text: 'text-green-600', border: 'border-green-300' } },
  dative: { id: 'dative', label: 'Dative (кому? чему?)', hint: '', color: { bg: 'bg-orange-100', text: 'text-orange-600', border: 'border-orange-300' } },
  accusative: { id: 'accusative', label: 'Accusative (кого? что?)', hint: '', color: { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-300' } },
  instrumental: { id: 'instrumental', label: 'Instrumental (кем? чем?)', hint: '', color: { bg: 'bg-pink-100', text: 'text-pink-600', border: 'border-pink-300' } },
  prepositional: { id: 'prepositional', label: 'Prepositional (о ком? о чём?)', hint: '', color: { bg: 'bg-cyan-100', text: 'text-cyan-600', border: 'border-cyan-300' } },
};

export const PatternIntro: React.FC<PatternIntroProps> = ({ pattern, examples, onComplete, grammarConfig }) => {
  const [step, setStep] = useState(0);
  const totalSteps = 2 + examples.length;

  // Build case config map from grammar config or use defaults
  const caseConfigs = useMemo(() => {
    if (!grammarConfig) return DEFAULT_CASES;
    return grammarConfig.cases.reduce((acc, c) => ({
      ...acc,
      [c.id]: { ...c, label: `${c.label} (${c.hint.split('(')[1]?.replace(')', '') || ''})` },
    }), {} as Record<string, CaseConfig>);
  }, [grammarConfig]);

  const getCaseConfig = (caseId: GrammaticalCase): CaseConfig => caseConfigs[caseId] || DEFAULT_CASES[caseId];

  const handleNext = useCallback(() => {
    if (step < totalSteps - 1) {
      setStep(s => s + 1);
    } else {
      onComplete();
    }
  }, [step, totalSteps, onComplete]);

  const progress = ((step + 1) / totalSteps) * 100;

  // Word breakdown component
  const WordBreakdown: React.FC<{ stem: string; ending: string; caseType: GrammaticalCase }> = ({ stem, ending, caseType }) => (
    <span className="font-mono text-xl">
      <span className="text-gray-600">{stem}</span>
      <span className={clsx('font-bold', getCaseConfig(caseType).color.text)}>{ending || '∅'}</span>
    </span>
  );

  return (
    <div className="flex flex-col h-full max-w-2xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <BookOpen className="text-indigo-500" size={20} />
          <span className="font-bold text-gray-700">Pattern Lesson</span>
        </div>
        <span className="text-gray-400 font-mono">{step + 1}/{totalSteps}</span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full mb-8 overflow-hidden">
        <motion.div className="h-full bg-indigo-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ duration: 0.3 }}
          className="flex-1 flex flex-col"
        >
          {step === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 bg-indigo-100 rounded-2xl flex items-center justify-center mb-6">
                <BookOpen className="text-indigo-600" size={40} />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-3">{pattern.name}</h2>
              <p className="text-lg text-gray-600 mb-8 max-w-md">{pattern.description}</p>

              {/* Pattern preview table */}
              <div className="bg-gray-50 rounded-xl p-6 w-full max-w-md">
                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">Ending Pattern</h3>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="font-bold text-gray-600">Case</div>
                  <div className="font-bold text-gray-600">Singular</div>
                  <div className="font-bold text-gray-600">Plural</div>
                  {(['nominative', 'genitive', 'dative', 'accusative'] as GrammaticalCase[]).map(c => (
                    <React.Fragment key={c}>
                      <div className="capitalize text-gray-700">{c.slice(0, 3)}.</div>
                      <div className={clsx('font-mono font-bold', getCaseConfig(c).color.text)}>-{pattern.paradigm[c]?.singular || '∅'}</div>
                      <div className={clsx('font-mono font-bold', getCaseConfig(c).color.text)}>-{pattern.paradigm[c]?.plural || '∅'}</div>
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step > 0 && step <= examples.length && (
            <div className="flex-1 flex flex-col items-center justify-center">
              {(() => {
                const example = examples[step - 1];
                return (
                  <>
                    <div className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Example {step} of {examples.length}</div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-1">{example.word}</h3>
                    <p className="text-gray-500 mb-8">{example.translation}</p>

                    {/* Declension examples */}
                    <div className="w-full max-w-md space-y-3">
                      {example.forms.map(({ case: c, form, ending }, idx) => (
                        <motion.div
                          key={c}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.1 * idx }}
                          className={clsx('flex items-center justify-between p-3 rounded-lg', getCaseConfig(c).color.bg)}
                        >
                          <span className="text-sm font-medium text-gray-700 capitalize">{c}</span>
                          <div className="flex items-center gap-3">
                            <WordBreakdown stem={example.stem} ending={ending} caseType={c} />
                            <span className="text-gray-400">→</span>
                            <span className="font-bold text-gray-900">{form}</span>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-xl p-4 w-full max-w-md">
                      <div className="flex items-start gap-3">
                        <Lightbulb className="text-yellow-500 flex-shrink-0 mt-0.5" size={18} />
                        <p className="text-yellow-800 text-sm">
                          Notice how the stem <span className="font-mono font-bold">{example.stem}</span> stays the same—only the ending changes!
                        </p>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          )}

          {step === totalSteps - 1 && (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 bg-green-100 rounded-2xl flex items-center justify-center mb-6">
                <Check className="text-green-600" size={40} />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-3">Ready to Practice!</h2>
              <p className="text-lg text-gray-600 mb-8 max-w-md">Now let's see if you can apply the <strong>{pattern.name}</strong> pattern.</p>

              <div className="bg-indigo-50 rounded-xl p-6 w-full max-w-md">
                <h3 className="text-sm font-bold text-indigo-700 uppercase tracking-wider mb-3">Remember</h3>
                <ul className="text-left text-indigo-900 space-y-2">
                  <li className="flex items-start gap-2"><span className="text-indigo-500 mt-1">•</span><span>The stem stays constant</span></li>
                  <li className="flex items-start gap-2"><span className="text-indigo-500 mt-1">•</span><span>Each case has a predictable ending</span></li>
                  <li className="flex items-start gap-2"><span className="text-indigo-500 mt-1">•</span><span>Words of the same type follow the same pattern</span></li>
                </ul>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <button
        onClick={handleNext}
        className={clsx(
          'mt-8 w-full py-4 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2',
          step === totalSteps - 1 ? 'bg-green-500 hover:bg-green-600 text-white' : 'bg-indigo-500 hover:bg-indigo-600 text-white'
        )}
      >
        {step === totalSteps - 1 ? (<><Check size={20} />Start Practice</>) : (<>Continue<ChevronRight size={20} /></>)}
      </button>
    </div>
  );
};

export default PatternIntro;
