import React from 'react';
import Username from './Username';
import SearchBar from './SearchBar';

const Header = () => {
  return (
    <header className="flex justify-between items-center p-4 bg-mint-dark/50 backdrop-blur-lg sticky top-0 z-40">
      <div className="text-2xl font-bold text-mint-primary font-display">MixMint</div>
      <div className="flex-1 flex justify-center px-8">
        <SearchBar />
      </div>
      <div className="flex items-center space-x-4">
        <Username />
      </div>
    </header>
  );
};

export default Header;
