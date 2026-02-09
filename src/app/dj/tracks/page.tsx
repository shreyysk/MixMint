"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useAuth } from "@/lib/AuthContext";
import RequireRole from "@/components/features/auth/RequireRole";
import { downloadContent } from "@/lib/download";

type Track = {
  id: string;
  title: string;
  price: number;
  created_at: string;
};

export default function DJTracksPage() {
  const { user, loading } = useAuth();
  const [tracks, setTracks] = useState<any[]>([]);
  const [albumPacks, setAlbumPacks] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(true);

  useEffect(() => {
    const loadContent = async () => {
      setLoadingContent(true);
      setError(null);

      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        console.warn("No valid session found");
        setError("Session not available");
        setLoadingContent(false);
        return;
      }

      const res = await fetch("/api/dj/tracks", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      const json = await res.json();
      console.log("DJ content response:", json);

      if (!res.ok) {
        setError(json.error || "Failed to load content");
      } else {
        setTracks(json.tracks || []);
        setAlbumPacks(json.albumPacks || []);
      }

      setLoadingContent(false);
    };

    if (user && !loading) {
      loadContent();
    }
  }, [user, loading]);

  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="p-6 text-white max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Content Manager</h1>

        {loadingContent && <p className="opacity-60">Loading your content...</p>}
        {!loadingContent && error && <p className="text-red-400 bg-red-400/10 p-4 rounded mb-6">{error}</p>}

        {/* SECTION: TRACKS */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
            <span>🎵</span> Individual Tracks
          </h2>
          {!loadingContent && tracks.length === 0 && (
            <p className="opacity-60 italic">No tracks uploaded yet.</p>
          )}
          <div className="grid grid-cols-1 gap-4">
            {tracks.map((track) => (
              <div key={track.id} className="bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold">{track.title}</h3>
                  <span className="bg-purple-600/30 text-purple-300 text-xs px-2 py-1 rounded">Track</span>
                </div>
                <p className="text-xl text-purple-400 font-mono mb-3">₹{track.price}</p>
                <p className="text-xs opacity-50 mb-4">
                  Uploaded {new Date(track.created_at).toLocaleDateString()}
                </p>
                <button
                  onClick={() => downloadContent(track.id, "track")}
                  className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg font-semibold transition-all"
                >
                  Download Source
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* SECTION: ALBUM PACKS */}
        <section>
          <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
            <span>📦</span> Album Packs (ZIP/RAR)
          </h2>
          {!loadingContent && albumPacks.length === 0 && (
            <p className="opacity-60 italic">No album packs uploaded yet.</p>
          )}
          <div className="grid grid-cols-1 gap-4">
            {albumPacks.map((pack) => (
              <div key={pack.id} className="bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors border-l-4 border-l-purple-500">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold">{pack.title}</h3>
                  <span className="bg-blue-600/30 text-blue-300 text-xs px-2 py-1 rounded">ZIP Pack</span>
                </div>
                {pack.description && <p className="text-sm opacity-70 mb-3">{pack.description}</p>}
                <p className="text-xl text-purple-400 font-mono mb-3">₹{pack.price}</p>
                <p className="text-xs opacity-50 mb-4">
                  Uploaded {new Date(pack.created_at).toLocaleDateString()}
                </p>
                <button
                  onClick={() => downloadContent(pack.id, "album")}
                  className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold transition-all"
                >
                  Download Bundle
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </RequireRole>
  );
}
