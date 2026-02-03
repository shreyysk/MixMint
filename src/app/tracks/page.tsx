"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { TrackCard } from "@/app/components/ui/TrackCard";
import { Loader2, Music } from "lucide-react";
import { motion } from "framer-motion";

interface Track {
  id: string;
  title: string;
  price: number;
  youtube_url: string | null;
  dj_id: string;
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
}

export default function TracksPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    loadTracks();
  }, []);

  async function loadTracks() {
    try {
      setLoading(true);
      setError(null);

      // Fetch tracks with DJ profile data
      const { data, error: fetchError } = await supabase
        .from("tracks")
        .select(`
          id,
          title,
          price,
          youtube_url,
          dj_id,
          dj_profiles:dj_id (
            dj_name,
            slug
          )
        `)
        .eq("status", "active")
        .order("created_at", { ascending: false });

      if (fetchError) throw fetchError;

      // Transform the data to match our interface
      const transformedData = (data || []).map((track: any) => ({
        ...track,
        dj_profile: Array.isArray(track.dj_profiles) 
          ? track.dj_profiles[0] 
          : track.dj_profiles
      }));

      setTracks(transformedData);
    } catch (err: any) {
      console.error("[TRACKS_LOAD_ERROR]", err);
      setError(err.message || "Failed to load tracks");
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload(trackId: string) {
    if (!user) {
      alert("Please log in to download tracks");
      window.location.href = "/auth/login";
      return;
    }

    try {
      // Get session token
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        alert("Please log in to download");
        return;
      }

      // Request download token
      const res = await fetch("/api/download-token", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}` 
        },
        body: JSON.stringify({ 
          content_id: trackId, 
          content_type: "track" 
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Download failed");
        return;
      }

      // Redirect to download
      window.location.href = `/api/download?token=${data.token}`;
    } catch (err: any) {
      console.error("[DOWNLOAD_ERROR]", err);
      alert("Download failed: " + err.message);
    }
  }

  return (
    <div className="pb-24" data-testid="tracks-page">
      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-16"
          >
            <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
              All <span className="text-violet-gradient">Tracks</span>
            </h1>
            <p className="text-zinc-500 font-bold max-w-lg">
              Browse all available tracks from our DJ community. Purchase individual tracks or subscribe to your favorite artists.
            </p>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24" data-testid="loading-state">
              <Loader2 className="animate-spin text-violet-500 mb-4" size={48} />
              <p className="text-zinc-500 font-bold">Loading tracks...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-8 rounded-2xl bg-red-900/20 border border-red-800/50 text-center" data-testid="error-state">
              <p className="text-red-400 font-bold mb-2">Failed to load tracks</p>
              <p className="text-red-500/70 text-sm mb-4">{error}</p>
              <button
                onClick={loadTracks}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white font-bold text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && tracks.length === 0 && (
            <div className="text-center py-24" data-testid="empty-state">
              <Music className="text-zinc-700 mx-auto mb-4" size={64} />
              <h3 className="text-2xl font-black text-white uppercase mb-2">No Tracks Available</h3>
              <p className="text-zinc-500 font-bold">No tracks have been uploaded yet. Check back soon!</p>
            </div>
          )}

          {/* Tracks Grid */}
          {!loading && !error && tracks.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              data-testid="tracks-grid"
            >
              {tracks.map((track) => (
                <TrackCard
                  key={track.id}
                  id={track.id}
                  title={track.title}
                  price={track.price}
                  djName={track.dj_profile?.dj_name}
                  djSlug={track.dj_profile?.slug}
                  youtubeUrl={track.youtube_url}
                  onDownload={handleDownload}
                />
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
