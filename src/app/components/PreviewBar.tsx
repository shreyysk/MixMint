'use client';

import React, { useRef, useEffect } from 'react';
import { usePlayer } from '../context/PlayerContext';
import { PlayIcon, PauseIcon } from '@heroicons/react/24/solid'; // Using icons for controls

const PreviewBar = () => {
  const { track, isPlaying, togglePlay } = usePlayer();
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch(error => console.error("Audio play failed:", error));
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, track]);

  if (!track) {
    return (
      <div className="fixed bottom-0 left-0 right-0 h-20 bg-mint-dark/80 backdrop-blur-lg z-50 flex items-center justify-center px-6 shadow-purple-glow">
        <p className="text-mint-accent">Select a track to preview</p>
      </div>
    );
  }

  // This handles when the track changes
  const onTrackEnded = () => {
    // For now, just pause. Later, we could implement auto-play next.
    togglePlay();
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 h-20 bg-mint-dark/80 backdrop-blur-lg z-50 flex items-center px-6 shadow-purple-glow">
      <div className="w-full flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Placeholder for Album Art */}
          <div className="w-12 h-12 bg-mint-secondary rounded-md"></div>
          <div>
            <p className="text-mint-studio font-bold">{track.title}</p>
            <p className="text-mint-accent text-sm">{track.artist}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
           <button onClick={togglePlay} className="p-2 rounded-full bg-mint-primary/50 hover:bg-mint-primary/80 text-white">
            {isPlaying ? (
              <PauseIcon className="h-6 w-6" />
            ) : (
              <PlayIcon className="h-6 w-6" />
            )}
          </button>
        </div>

        <div className="text-mint-accent text-sm">
          Preview Only
        </div>
        
        <audio
          ref={audioRef}
          src={track.url}
          onEnded={onTrackEnded}
          className="hidden" // The audio element itself is not visible
        />
      </div>
    </div>
  );
};

export default PreviewBar;
