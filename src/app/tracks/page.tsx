"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { TrackCard } from "@/app/components/ui/TrackCard";
import { Loader2, Music, Search } from "lucide-react";
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
  const [searchQuery, setSearchQuery] = useState("");
  const { user } = useAuth();

  useEffect(() => {
    loadTracks();
  }, []);

  async function loadTracks() {
    try {
      setLoading(true);
      setError(null);

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
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        alert("Please log in to download");
        return;
      }

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

      window.location.href = `/api/download?token=${data.token}`;
    } catch (err: any) {
      console.error("[DOWNLOAD_ERROR]", err);
      alert("Download failed: " + err.message);
    }
  }

  // Filter tracks based on search
  const filteredTracks = tracks.filter((track) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      track.title.toLowerCase().includes(query) ||
      track.dj_profile?.dj_name?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen pb-24" data-testid="tracks-page">
      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 mb-12"
          >
            <div>
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
                All <span className="text-violet-gradient">Tracks</span>
              </h1>
              <p className="text-zinc-500 max-w-lg">
                Browse individual tracks from our DJ community. Purchase or preview before buying.
              </p>
            </div>

            {/* Search */}
            <div className="relative group w-full lg:w-auto">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-violet-400 transition-colors" size={18} />
              <input
                type="text"
                placeholder="Search tracks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full lg:w-72 bg-zinc-900/60 border border-zinc-800/60 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600"
                data-testid="track-search-input"
              />
            </div>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-32" data-testid="loading-state">
              <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center mb-6">
                <Loader2 className="animate-spin text-violet-400" size={28} />
              </div>
              <p className="text-zinc-500">Loading tracks...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-2xl bg-red-900/10 border border-red-800/30 text-center max-w-md mx-auto" 
              data-testid="error-state"
            >
              <p className="text-red-400 font-medium mb-2">Failed to load tracks</p>
              <p className="text-red-500/60 text-sm mb-4">{error}</p>
              <button
                onClick={loadTracks}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl text-white font-medium text-sm transition-colors"
              >
                Try Again
              </button>
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredTracks.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-32" 
              data-testid="empty-state"
            >
              <div className="w-20 h-20 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-center mx-auto mb-6">
                <Music className="text-zinc-600" size={32} />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No Tracks Found</h3>
              <p className="text-zinc-500">
                {searchQuery ? `No results for "${searchQuery}"` : "No tracks available yet. Check back soon!"}
              </p>
            </motion.div>
          )}

          {/* Tracks Grid */}
          {!loading && !error && filteredTracks.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
              data-testid="tracks-grid"
            >
              {filteredTracks.map((track) => (
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
