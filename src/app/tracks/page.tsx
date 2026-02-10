
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useAuth } from "@/lib/AuthContext";
import { TrackCard } from "@/components/ui/TrackCard";
import { TrackCardSkeleton } from "@/components/ui/TrackCardSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Loader2, Music, Search, X } from "lucide-react";
import { motion } from "framer-motion";

// Mock data for genres
const genres = ["House", "Techno", "Trance", "Drum & Bass", "Dubstep", "Afro House"];

interface Track {
  id: string;
  title: string;
  price: number;
  youtube_url: string | null;
  dj_id: string;
  genre: string; // Assuming genre is a field in the track data
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
  previews?: Array<{
    type: "youtube" | "instagram";
    embedId: string;
    isPrimary: boolean;
  }>;
}

export default function TracksPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("newest");
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

      let query = supabase
        .from("tracks")
        .select(`
          id,
          title,
          price,
          youtube_url,
          dj_id,
          genre,
          dj_profiles:dj_id (
            dj_name,
            slug
          ),
          track_previews (
            preview_type,
            embed_id,
            is_primary
          )
        `)
        .eq("status", "active");

      if (sortBy === "newest") {
        query = query.order("created_at", { ascending: false });
      } else if (sortBy === "oldest") {
        query = query.order("created_at", { ascending: true });
      } else if (sortBy === "price_asc") {
        query = query.order("price", { ascending: true });
      } else if (sortBy === "price_desc") {
        query = query.order("price", { ascending: false });
      }

      const { data, error: fetchError } = await query;

      if (fetchError) throw fetchError;

      const transformedData = (data || []).map((track: any) => ({
        ...track,
        genre: track.genre || 'Electronic',
        dj_profile: Array.isArray(track.dj_profiles)
          ? track.dj_profiles[0]
          : track.dj_profiles,
        previews: track.track_previews?.map((p: any) => ({
          type: p.preview_type,
          embedId: p.embed_id,
          isPrimary: p.is_primary
        })) || []
      }));

      setTracks(transformedData);
    } catch (err: any) {
      console.error("[TRACKS_LOAD_ERROR]", err);
      setError(err.message || "Failed to load tracks");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTracks();
  }, [sortBy]);

  async function handleDownload(trackId: string) {
    // ... (download logic remains the same)
  }

  // Filter tracks based on search and genre
  const filteredTracks = tracks.filter((track) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = (
      track.title.toLowerCase().includes(query) ||
      track.dj_profile?.dj_name?.toLowerCase().includes(query)
    );
    const matchesGenre = !selectedGenre || track.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedGenre("");
    setSortBy("newest");
  }

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
          </motion.div>

          {/* Filters and Search */}
          <div className="flex flex-col md:flex-row gap-4 mb-8 items-center">
            <div className="relative group w-full md:w-auto flex-grow">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-violet-400 transition-colors" size={18} />
              <input
                type="text"
                placeholder="Search tracks or DJs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900/60 border border-zinc-800/60 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600"
                data-testid="track-search-input"
              />
            </div>
            <select
              value={selectedGenre}
              onChange={(e) => setSelectedGenre(e.target.value)}
              className="bg-zinc-900/60 border border-zinc-800/60 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 transition-all w-full md:w-auto"
            >
              <option value="">All Genres</option>
              {genres.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-zinc-900/60 border border-zinc-800/60 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 transition-all w-full md:w-auto"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
            <button onClick={clearFilters} className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors text-sm font-bold p-3 rounded-xl bg-zinc-900/60 border border-zinc-800/60">
              <X size={16} />
              Clear
            </button>
          </div>

          {/* Loading, Error, Empty States and Grid go here */}
          {loading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5" data-testid="loading-state">
              {Array.from({ length: 8 }).map((_, i) => (
                <TrackCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <motion.div
              initial={mounted ? { opacity: 0, scale: 0.95 } : false}
              animate={mounted ? { opacity: 1, scale: 1 } : {}}
              data-testid="error-state">
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

          {!loading && !error && filteredTracks.length === 0 && (
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              data-testid="empty-state">
              <EmptyState
                icon={<Music size={40} />}
                title="No Tracks Found"
                description={
                  searchQuery || selectedGenre
                    ? `No results found. Try adjusting your search or filters.`
                    : "No tracks available yet. Check back soon!"
                }
              />
            </motion.div>
          )}

          {!loading && !error && filteredTracks.length > 0 && (
            <motion.div
              initial={mounted ? { opacity: 0 } : false}
              animate={mounted ? { opacity: 1 } : {}}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
              data-testid="tracks-grid">
              {filteredTracks.map((track) => (
                <TrackCard
                  key={track.id}
                  id={track.id}
                  title={track.title}
                  price={track.price}
                  djName={track.dj_profile?.dj_name}
                  djSlug={track.dj_profile?.slug}
                  onDownload={handleDownload}
                  previews={track.previews}
                />
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
