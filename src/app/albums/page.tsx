"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { AlbumCard } from "@/app/components/ui/AlbumCard";
import { Loader2, Package } from "lucide-react";
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
  const { user } = useAuth();

  useEffect(() => {
    loadAlbums();
  }, []);

  async function loadAlbums() {
    try {
      setLoading(true);
      setError(null);

      // Fetch albums with DJ profile data
      // Note: album_packs.dj_id points to profiles.id, not dj_profiles.id
      const { data: albumsData, error: albumsError } = await supabase
        .from("album_packs")
        .select("id, title, description, price, file_size, dj_id")
        .order("created_at", { ascending: false });

      if (albumsError) throw albumsError;

      // Fetch DJ profiles separately due to schema inconsistency
      if (albumsData && albumsData.length > 0) {
        const djIds = [...new Set(albumsData.map(a => a.dj_id))];
        
        const { data: djProfiles } = await supabase
          .from("dj_profiles")
          .select("user_id, dj_name, slug")
          .in("user_id", djIds);

        // Map DJ data to albums
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
          content_id: albumId, 
          content_type: "zip" 
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
    <div className="pb-24" data-testid="albums-page">
      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-16"
          >
            <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
              Album <span className="text-amber-gradient">Packs</span>
            </h1>
            <p className="text-zinc-500 font-bold max-w-lg">
              Complete collections from our DJs. Each album pack is a curated ZIP file with multiple tracks.
            </p>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24" data-testid="loading-state">
              <Loader2 className="animate-spin text-amber-500 mb-4" size={48} />
              <p className="text-zinc-500 font-bold">Loading album packs...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-8 rounded-2xl bg-red-900/20 border border-red-800/50 text-center" data-testid="error-state">
              <p className="text-red-400 font-bold mb-2">Failed to load albums</p>
              <p className="text-red-500/70 text-sm mb-4">{error}</p>
              <button
                onClick={loadAlbums}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white font-bold text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && albums.length === 0 && (
            <div className="text-center py-24" data-testid="empty-state">
              <Package className="text-zinc-700 mx-auto mb-4" size={64} />
              <h3 className="text-2xl font-black text-white uppercase mb-2">No Album Packs Available</h3>
              <p className="text-zinc-500 font-bold">No album packs have been uploaded yet. Check back soon!</p>
            </div>
          )}

          {/* Albums Grid */}
          {!loading && !error && albums.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              data-testid="albums-grid"
            >
              {albums.map((album) => (
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
