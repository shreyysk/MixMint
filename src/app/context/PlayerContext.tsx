'use client';

import React, { createContext, useState, useContext, ReactNode } from 'react';

interface Track {
  title: string;
  artist: string;
  url: string; // Assuming we have a URL for the track
}

interface PlayerContextType {
  track: Track | null;
  isPlaying: boolean;
  playTrack: (track: Track) => void;
  togglePlay: () => void;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export const usePlayer = () => {
  const context = useContext(PlayerContext);
  if (!context) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return context;
};

export const PlayerProvider = ({ children }: { children: ReactNode }) => {
  const [track, setTrack] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const playTrack = (newTrack: Track) => {
    setTrack(newTrack);
    setIsPlaying(true);
  };

  const togglePlay = () => {
    if (track) {
      setIsPlaying(!isPlaying);
    }
  };

  const value = {
    track,
    isPlaying,
    playTrack,
    togglePlay,
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
    </PlayerContext.Provider>
  );
};
