import React, { useState } from 'react';

const DownloadButton = () => {
  const [status, setStatus] = useState('idle'); // idle, validating, minting, ready
  const [attempts, setAttempts] = useState(3);

  const handleClick = () => {
    if (status === 'idle') {
      setStatus('validating');
      setTimeout(() => {
        setStatus('minting');
        setTimeout(() => {
          setStatus('ready');
        }, 2000);
      }, 1500);
    }
  };

  return (
    <div className="flex items-center space-x-4">
      <button
        onClick={handleClick}
        className={`relative w-48 h-12 px-6 py-2 rounded-full font-bold text-white transition-all duration-300 overflow-hidden ${
          status === 'idle' ? 'bg-mint-primary' :
          status === 'validating' ? 'bg-mint-secondary' :
          status === 'minting' ? 'bg-mint-secondary' :
          'bg-green-500'
        }`}
      >
        <span className="relative z-10">
          {status === 'idle' && 'Download'}
          {status === 'validating' && <span className="animate-pulse">Validating...</span>}
          {status === 'minting' && <span className="animate-pulse">Minting Token...</span>}
          {status === 'ready' && 'Download Ready'}
        </span>
        {status === 'validating' && (
          <div className="absolute inset-0 rounded-full bg-mint-primary animate-ping"></div>
        )}
        {status === 'minting' && (
          <div className="absolute top-0 left-0 h-full w-0 bg-white/30 animate-[shimmer_2s_infinite]"></div>
        )}
      </button>
      <div className="text-sm text-mint-accent">
        <p>Attempts remaining: {attempts}/3</p>
      </div>
    </div>
  );
};

export default DownloadButton;
