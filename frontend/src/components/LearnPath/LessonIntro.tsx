import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, BookOpen, Volume2 } from 'lucide-react';

interface LessonIntroProps {
    title: string;
    description: string;
    content: {
        introduction?: string;
    };
    vocabulary: Array<{
        word: string;
        translation: string;
        audio?: string;
    }>;
    onStart: () => void;
}

export const LessonIntro: React.FC<LessonIntroProps> = ({
    title,
    description,
    content,
    vocabulary,
    onStart,
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto mt-8 pb-20"
        >
            <div className="bg-white rounded-3xl shadow-xl p-8 md:p-12 border border-gray-100">
                <div className="w-20 h-20 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <BookOpen size={40} />
                </div>

                <h1 className="text-3xl font-black text-gray-900 mb-4 text-center">{title}</h1>
                <p className="text-gray-500 text-lg mb-8 text-center max-w-lg mx-auto">
                    {description}
                </p>

                {/* Theory Section */}
                {content.introduction && (
                    <div className="bg-blue-50 rounded-2xl p-6 mb-8 prose prose-blue max-w-none">
                        <div className="whitespace-pre-wrap font-medium text-gray-800">
                            {content.introduction}
                        </div>
                    </div>
                )}

                {/* Vocabulary Preview */}
                {vocabulary.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-4">New Words</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {vocabulary.map((item, idx) => (
                                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100 hover:border-primary-200 transition-colors group">
                                    <div>
                                        <div className="font-bold text-gray-900">{item.word}</div>
                                        <div className="text-sm text-gray-500">{item.translation}</div>
                                    </div>
                                    {item.audio && (
                                        <button className="p-2 text-gray-400 hover:text-primary-600 hover:bg-white rounded-full transition-all shadow-sm opacity-0 group-hover:opacity-100">
                                            <Volume2 size={16} />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <button
                    onClick={onStart}
                    className="w-full bg-primary-600 text-white font-bold py-4 px-8 rounded-xl hover:bg-primary-700 transition-all transform hover:scale-[1.02] shadow-lg shadow-primary-200 flex items-center justify-center gap-2"
                >
                    Start Lesson <ArrowRight size={20} />
                </button>
            </div>
        </motion.div>
    );
};
