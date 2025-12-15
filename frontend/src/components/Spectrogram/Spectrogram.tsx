import React, { useEffect, useRef } from 'react';

interface SpectrogramProps {
  audioContext: AudioContext | null;
  mediaStream: MediaStream | null;
  width?: number;
  height?: number;
  active: boolean;
}

export const Spectrogram: React.FC<SpectrogramProps> = ({
  audioContext,
  mediaStream,
  width = 600,
  height = 200,
  active,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationIdRef = useRef<number | null>(null);
  
  // Setup audio graph
  useEffect(() => {
    if (!audioContext || !mediaStream || !active) return;

    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.5;
    
    const source = audioContext.createMediaStreamSource(mediaStream);
    source.connect(analyser);
    
    analyserRef.current = analyser;
    sourceRef.current = source;

    return () => {
      source.disconnect();
      // Don't disconnect analyser here as it might be reused
    };
  }, [audioContext, mediaStream, active]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !active || !analyserRef.current) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas initially
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, width, height);

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    // We'll scroll the spectrogram from right to left
    // Need an offscreen canvas to store history
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');
    
    const draw = () => {
      if (!active || !analyserRef.current || !ctx) return;
      
      animationIdRef.current = requestAnimationFrame(draw);
      
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Shift everything to the left
      if (tempCtx) {
        tempCtx.drawImage(canvas, 0, 0, width, height);
        
        // Draw saved image shifted left by 1px
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(tempCanvas, -2, 0, width, height); // Shift speed
      }
      
      // Draw new column at the right edge
      const barWidth = 2;
      const x = width - barWidth;
      
      // We only care about up to ~5kHz for speech usually
      // bufferLength corresponds to Nyquist (half sample rate, e.g. 22050Hz)
      // We want to display more detail in lower frequencies
      const maxBin = Math.floor(bufferLength * 0.5); // Use half the range
      
      for (let i = 0; i < height; i++) {
        // Map y position (0 at top, height at bottom) to frequency bin
        // We want 0Hz at bottom, maxHz at top
        const ratio = 1 - (i / height);
        const binIndex = Math.floor(ratio * maxBin);
        
        const value = dataArray[binIndex];
        
        // Color mapping based on intensity
        const hue = (value / 255) * 280; // Map intensity to hue
        const saturation = 100;
        const lightness = (value / 255) * 50;
        
        ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        ctx.fillRect(x, i, barWidth, 1);
      }
    };

    draw();

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [active, width, height]);

  return (
    <canvas 
      ref={canvasRef} 
      width={width} 
      height={height}
      className="bg-black rounded border border-gray-700 w-full"
    />
  );
};

