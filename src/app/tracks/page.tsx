"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";

type Track = {
  id: string;
  title: string;
  price: number;
};

export default function TracksPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTracks() {
      const { data } = await supabase
        .from("tracks")
        .select("id, title, price")
        .order("created_at", { ascending: false });

      setTracks(data || []);
      setLoading(false);
    }

    loadTracks();
  }, []);

  //  CORRECT DOWNLOAD FLOW
  async function handleDownload(trackId: string) {
    // 0. Get Session (Required for Authorization header)
    const { data: { session } } = await supabase.auth.getSession();
    
    if (!session) {
      alert("Please log in to download.");
      return;
    }

    // 1. Ask backend for a NEW token
    const res = await fetch("/api/download-token", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}` 
      },
      // Note: Using content_id/content_type to match your backend logic
      body: JSON.stringify({ 
        content_id: trackId, 
        content_type: "track" 
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.error);
      return;
    }

    // 2. Immediately use token ONCE
    window.location.href = `/api/download?token=${data.token}`;
  }

  if (loading) {
    return <div className="p-6">Loading tracks...</div>;
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Tracks</h1>

      {tracks.length === 0 && <p>No tracks available</p>}

      {tracks.map((track) => (
        <div
          key={track.id}
          className="border border-white/20 rounded p-4 mb-4"
        >
          <p className="font-semibold">{track.title}</p>
          <p className="text-sm opacity-80">Price: ₹{track.price}</p>

          <button
            onClick={() => handleDownload(track.id)}
            className="mt-3 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded"
          >
            Download
          </button>
        </div>
      ))}
    </div>
  );
}