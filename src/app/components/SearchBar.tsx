'use client';

import React from 'react';
import { useSearch } from '../context/SearchContext';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

const SearchBar = () => {
  const { searchTerm, setSearchTerm } = useSearch();

  return (
    <div className="relative w-full max-w-md">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <MagnifyingGlassIcon className="h-5 w-5 text-mint-accent" />
      </div>
      <input
        type="text"
        placeholder="Search for tracks, artists, genres..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="w-full bg-mint-dark/50 border border-mint-secondary rounded-full py-2 pl-10 pr-4 text-white placeholder-mint-accent focus:outline-none focus:ring-2 focus:ring-mint-primary focus:border-transparent transition-all"
      />
    </div>
  );
};

export default SearchBar;
