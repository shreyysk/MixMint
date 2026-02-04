"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { TrackCard } from "@/app/components/ui/TrackCard";
import { TrackCardSkeleton } from "@/app/components/ui/TrackCardSkeleton";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { ErrorBanner } from "@/app/components/ui/ErrorBanner";
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
  const [mounted, setMounted] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    setMounted(true);
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
            initial={mounted ? { opacity: 0, y: 20 } : false}
            animate={mounted ? { opacity: 1, y: 0 } : {}}
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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5" data-testid="loading-state">
              {Array.from({ length: 8 }).map((_, i) => (
                <TrackCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Error State */}
          {error && (
            <motion.div
              initial={mounted ? { opacity: 0, scale: 0.95 } : false}
              animate={mounted ? { opacity: 1, scale: 1 } : {}}
              data-testid="error-state"
            >
              <ErrorBanner
                title="Failed to load tracks"
                message={error}
                action={{
                  label: "Try Again",
                  onClick: loadTracks
                }}
                variant="error"
              />
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredTracks.length === 0 && (
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              data-testid="empty-state"
            >
              <EmptyState
                icon={<Music size={40} />}
                title="No Tracks Found"
                description={
                  searchQuery
                    ? `No results for "${searchQuery}". Try a different search term.`
                    : "No tracks available yet. Check back soon for fresh releases!"
                }
                action={{
                  label: "Explore DJs",
                  href: "/explore"
                }}
              />
            </motion.div>
          )}

          {/* Tracks Grid */}
          {!loading && !error && filteredTracks.length > 0 && (
            <motion.div
              initial={mounted ? { opacity: 0 } : false}
              animate={mounted ? { opacity: 1 } : {}}
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
