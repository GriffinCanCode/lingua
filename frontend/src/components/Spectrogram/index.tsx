import React, { useState, useEffect, useRef } from 'react';
import { Spectrogram } from './Spectrogram';
import { phoneticsService, MinimalPair } from '../../services/phonetics';
import { Mic, Square } from 'lucide-react';

export const PhoneticsTrainer: React.FC = () => {
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [pairs, setPairs] = useState<MinimalPair[]>([]);
  const [currentPairIndex, setCurrentPairIndex] = useState(0);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    loadPairs();
    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
      }
      if (audioContext) {
        audioContext.close();
      }
    };
  }, []);

  const loadPairs = async () => {
    try {
      const data = await phoneticsService.getMinimalPairs();
      setPairs(data);
    } catch (err) {
      console.error(err);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      setMediaStream(stream);
      setAudioContext(context);
      setIsRecording(true);
      
      // Setup recording
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      
      recorder.ondataavailable = (e) => {
        chunksRef.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        // const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
        // Analyze audio
        // await phoneticsService.analyzeAudio(blob);
      };
      
      recorder.start();
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Don't close context immediately to allow review? 
      // For now we keep stream active for visualizer if needed, 
      // but toggle isRecording prop on visualizer
    }
  };

  const currentPair = pairs[currentPairIndex];

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-6">Phonological Awareness Trainer</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 text-gray-700">Minimal Pair Practice</h3>
          
          {currentPair ? (
            <div className="text-center py-8">
              <div className="text-sm text-gray-500 mb-2 uppercase tracking-wide">
                Contrast: {currentPair.contrast}
              </div>
              
              <div className="flex justify-center items-center gap-12 mb-8">
                <div>
                  <div className="text-4xl font-bold mb-2">{currentPair.word1}</div>
                  <div className="text-gray-500 font-mono">/{currentPair.ipa1}/</div>
                </div>
                <div className="text-2xl text-gray-300">vs</div>
                <div>
                  <div className="text-4xl font-bold mb-2">{currentPair.word2}</div>
                  <div className="text-gray-500 font-mono">/{currentPair.ipa2}/</div>
                </div>
              </div>
              
              <div className="text-gray-600 italic mb-8">
                "{currentPair.description}"
              </div>

              <div className="flex justify-center gap-4">
                <button 
                  onClick={() => setCurrentPairIndex(prev => (prev - 1 + pairs.length) % pairs.length)}
                  className="p-2 rounded hover:bg-gray-100"
                >
                  Previous
                </button>
                <button 
                  onClick={() => setCurrentPairIndex(prev => (prev + 1) % pairs.length)}
                  className="p-2 rounded hover:bg-gray-100"
                >
                  Next Pair
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">Loading pairs...</div>
          )}
        </div>

        <div className="bg-white p-6 rounded-lg shadow flex flex-col">
          <h3 className="text-lg font-semibold mb-4 text-gray-700">Real-time Feedback</h3>
          
          <div className="flex-1 bg-black rounded mb-4 overflow-hidden relative">
            <Spectrogram 
              audioContext={audioContext}
              mediaStream={mediaStream}
              active={isRecording}
              width={400}
              height={200}
            />
            {!isRecording && !mediaStream && (
                <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                    Press microphone to start
                </div>
            )}
          </div>

          <div className="flex justify-center gap-4">
            {!isRecording ? (
              <button
                onClick={startRecording}
                className="flex items-center gap-2 bg-red-600 text-white px-6 py-3 rounded-full hover:bg-red-700 transition shadow-lg"
              >
                <Mic size={20} /> Start Recording
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="flex items-center gap-2 bg-gray-800 text-white px-6 py-3 rounded-full hover:bg-gray-900 transition shadow-lg"
              >
                <Square size={20} /> Stop
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h4 className="font-bold text-blue-800 mb-2">How to use this tool</h4>
        <ul className="list-disc list-inside text-blue-700 space-y-1">
          <li>Listen to the distinction between the minimal pair words.</li>
          <li>Record yourself pronouncing each word.</li>
          <li>Watch the spectrogram to see visual differences in your pronunciation.</li>
          <li>Compare the formant patterns (horizontal bands of energy) for vowels like 'ы' vs 'и'.</li>
        </ul>
      </div>
    </div>
  );
};

