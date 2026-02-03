"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { AlbumCard } from "@/app/components/ui/AlbumCard";
import { Loader2, Package, Search } from "lucide-react";
import { motion } from "framer-motion";

interface Album {
  id: string;
  title: string;
  description: string | null;
  price: number;
  file_size: number;
  dj_id: string;
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
}

export default function AlbumsPage() {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const { user } = useAuth();

  useEffect(() => {
    loadAlbums();
  }, []);

  async function loadAlbums() {
    try {
      setLoading(true);
      setError(null);

      const { data: albumsData, error: albumsError } = await supabase
        .from("album_packs")
        .select("id, title, description, price, file_size, dj_id")
        .order("created_at", { ascending: false });

      if (albumsError) throw albumsError;

      if (albumsData && albumsData.length > 0) {
        const djIds = [...new Set(albumsData.map(a => a.dj_id))];
        
        const { data: djProfiles } = await supabase
          .from("dj_profiles")
          .select("user_id, dj_name, slug")
          .in("user_id", djIds);

        const albumsWithDJ = albumsData.map(album => ({
          ...album,
          dj_profile: djProfiles?.find(dj => dj.user_id === album.dj_id)
        }));

        setAlbums(albumsWithDJ);
      } else {
        setAlbums([]);
      }

    } catch (err: any) {
      console.error("[ALBUMS_LOAD_ERROR]", err);
      setError(err.message || "Failed to load albums");
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload(albumId: string) {
    if (!user) {
      alert("Please log in to download albums");
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
          content_id: albumId, 
          content_type: "zip" 
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

  // Filter albums based on search
  const filteredAlbums = albums.filter((album) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      album.title.toLowerCase().includes(query) ||
      album.description?.toLowerCase().includes(query) ||
      album.dj_profile?.dj_name?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen pb-24" data-testid="albums-page">
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
                Album <span className="text-amber-gradient">Packs</span>
              </h1>
              <p className="text-zinc-500 max-w-lg">
                Complete collections from our DJs. Each pack is a curated ZIP with multiple tracks.
              </p>
            </div>

            {/* Search */}
            <div className="relative group w-full lg:w-auto">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-amber-400 transition-colors" size={18} />
              <input
                type="text"
                placeholder="Search albums..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full lg:w-72 bg-zinc-900/60 border border-zinc-800/60 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-amber-500/50 transition-all placeholder:text-zinc-600"
                data-testid="album-search-input"
              />
            </div>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-32" data-testid="loading-state">
              <div className="w-16 h-16 rounded-2xl bg-amber-600/10 border border-amber-500/20 flex items-center justify-center mb-6">
                <Loader2 className="animate-spin text-amber-400" size={28} />
              </div>
              <p className="text-zinc-500">Loading album packs...</p>
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
              <p className="text-red-400 font-medium mb-2">Failed to load albums</p>
              <p className="text-red-500/60 text-sm mb-4">{error}</p>
              <button
                onClick={loadAlbums}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl text-white font-medium text-sm transition-colors"
              >
                Try Again
              </button>
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredAlbums.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-32" 
              data-testid="empty-state"
            >
              <div className="w-20 h-20 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-center mx-auto mb-6">
                <Package className="text-zinc-600" size={32} />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No Album Packs Found</h3>
              <p className="text-zinc-500">
                {searchQuery ? `No results for "${searchQuery}"` : "No album packs available yet. Check back soon!"}
              </p>
            </motion.div>
          )}

          {/* Albums Grid */}
          {!loading && !error && filteredAlbums.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
              data-testid="albums-grid"
            >
              {filteredAlbums.map((album) => (
                <AlbumCard
                  key={album.id}
                  id={album.id}
                  title={album.title}
                  description={album.description}
                  price={album.price}
                  fileSize={album.file_size}
                  djName={album.dj_profile?.dj_name}
                  djSlug={album.dj_profile?.slug}
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
