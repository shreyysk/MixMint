'use client';

import React from 'react';
import DownloadButton from './DownloadButton';
import { usePlayer } from '../context/PlayerContext';

type TrackCardProps = {
  tier: 'single' | 'zip' | 'fan';
  title: string;
  artist: string;
  trackUrl?: string; // Optional: URL for the track audio
};

const TrackCard: React.FC<TrackCardProps> = ({ tier, title, artist, trackUrl }) => {
  const { playTrack } = usePlayer();

  const isFanOnly = tier === 'fan';
  const isZipPack = tier === 'zip';

  const fanOnlyStyles = isFanOnly ? 'bg-super-gradient' : 'bg-mint-gradient';
  const zipPackStyles = isZipPack ? 'border-2 border-mint-accent scale-105' : 'border border-mint-secondary';

  const handleCardClick = () => {
    if (trackUrl) {
      playTrack({ title, artist, url: trackUrl });
    }
  };

  return (
    <div 
      className={`relative rounded-lg p-4 transition-transform duration-300 hover:scale-105 cursor-pointer ${zipPackStyles}`}
      onClick={handleCardClick}
    >
      <div className={`absolute inset-0 rounded-lg ${fanOnlyStyles} opacity-20`}></div>
      <div className="relative z-10">
        <div className="aspect-w-1 aspect-h-1 mb-4">
          {/* Placeholder for Album Art */}
          <div className="w-full h-full bg-mint-secondary rounded-md"></div>
        </div>
        <h3 className="font-bold text-lg text-mint-studio truncate">{title}</h3>
        <p className="text-mint-accent text-sm mb-4">{artist}</p>
        <DownloadButton tier={tier} />
        {isFanOnly && (
          <div className="absolute top-2 right-2 bg-super-gradient text-white text-xs font-bold px-2 py-1 rounded-full">
            Fan-Only
          </div>
        )}
        {isZipPack && (
          <div className="absolute top-2 right-2 bg-mint-gradient text-white text-xs font-bold px-2 py-1 rounded-full">
            ZIP Pack
          </div>
        )}
      </div>
    </div>
  );
};

export default TrackCard;
