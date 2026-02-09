"use client";

import React, { useState } from 'react';
import { Loader2, Download, Lock } from 'lucide-react';

interface Props {
  contentId: string;
  contentType: 'track' | 'zip';
  isOwned?: boolean; // If already purchased or subscribed
}

const DownloadButton = ({ contentId, contentType, isOwned = false }: Props) => {
  const [status, setStatus] = useState<'idle' | 'validating' | 'ready'>('idle');

  const handleClick = async () => {
    if (!isOwned) {
      // If not owned, button should probably link to purchase or show price
      // For now we'll assume the parent component handles purchase visibility
      return;
    }

    setStatus('validating');
    try {
      const res = await fetch("/api/download-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_id: contentId, content_type: contentType }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to generate download link");

      setStatus('ready');

      // Trigger download
      window.location.href = `/api/download?token=${data.token}`;

      // Reset after a delay
      setTimeout(() => setStatus('idle'), 3000);

    } catch (err: any) {
      alert(err.message);
      setStatus('idle');
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={status === 'validating'}
      className={`flex items-center justify-center gap-2 w-full h-10 px-4 rounded-full font-bold transition-all duration-300 ${!isOwned ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed' :
          status === 'idle' ? 'bg-mint-studio text-black hover:bg-mint-studio/90' :
            status === 'validating' ? 'bg-zinc-700 text-white' :
              'bg-green-500 text-white'
        }`}
    >
      {status === 'validating' ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          Validating...
        </>
      ) : !isOwned ? (
        <>
          <Lock className="w-4 h-4" />
          Locked
        </>
      ) : (
        <>
          <Download className="w-4 h-4" />
          {status === 'idle' ? 'Download Now' : 'Downloading...'}
        </>
      )}
    </button>
  );
};

export default DownloadButton;
