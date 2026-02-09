'use client';

import React from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import TrackCard from './components/TrackCard';
import { useSearch } from './context/SearchContext';

const tracks = [
  {
    tier: 'single',
    title: 'Techno Dreams',
    artist: 'DJ Velocity',
    trackUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
  },
  {
    tier: 'zip',
    title: 'House Essentials Vol. 3',
    artist: 'ClubMaster',
    trackUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
  },
  {
    tier: 'fan',
    title: 'Exclusive Remix',
    artist: 'VIP Producer',
    trackUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
  },
  {
    tier: 'single',
    title: 'Future Bass Anthem',
    artist: 'Synthwave Kid',
    trackUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3',
  },
];

export default function Home() {
  const { searchTerm } = useSearch();

  const filteredTracks = tracks.filter((track) =>
    track.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    track.artist.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-8">
          <h1 className="text-4xl font-bold font-display mb-8 text-mint-primary">Latest Releases</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {filteredTracks.length > 0 ? (
              filteredTracks.map((track, index) => (
                <TrackCard key={index} {...track} />
              ))
            ) : (
              <p className="text-mint-accent col-span-full">No tracks found.</p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
