"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { supabase } from "@/app/lib/supabaseClient";
import { TrackCard } from "@/app/components/ui/TrackCard";
import { AlbumCard } from "@/app/components/ui/AlbumCard";
import { Button } from "@/app/components/ui/Button";
import { Loader2, Music, Package, Users } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

interface DJProfile {
  id: string;
  user_id: string;
  dj_name: string;
  slug: string;
  bio: string | null;
  genres: string[] | null;
  banner_url: string | null;
}

interface Track {
  id: string;
  title: string;
  price: number;
  youtube_url: string | null;
}

interface Album {
  id: string;
  title: string;
  description: string | null;
  price: number;
  file_size: number;
}

export default function DJProfilePage() {
  const params = useParams();
  const slug = params?.slug as string;

  const [dj, setDJ] = useState<DJProfile | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (slug) {
      loadDJProfile();
    }
  }, [slug]);

  async function loadDJProfile() {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch DJ Profile
      const { data: djData, error: djError } = await supabase
        .from("dj_profiles")
        .select("*")
        .eq("slug", slug)
        .eq("status", "approved")
        .single();

      if (djError) throw new Error("DJ not found");
      if (!djData) throw new Error("DJ not found");

      setDJ(djData);

      // 2. Fetch Tracks (using dj_profile.id)
      const { data: tracksData } = await supabase
        .from("tracks")
        .select("id, title, price, youtube_url")
        .eq("dj_id", djData.id)
        .eq("status", "active")
        .order("created_at", { ascending: false });

      setTracks(tracksData || []);

      // 3. Fetch Albums (using profile.user_id due to schema inconsistency)
      const { data: albumsData } = await supabase
        .from("album_packs")
        .select("id, title, description, price, file_size")
        .eq("dj_id", djData.user_id)
        .order("created_at", { ascending: false });

      setAlbums(albumsData || []);

    } catch (err: any) {
      console.error("[DJ_PROFILE_ERROR]", err);
      setError(err.message || "Failed to load DJ profile");
    } finally {
      setLoading(false);
    }
  }

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="loading-state">
        <div className="text-center">
          <Loader2 className="animate-spin text-violet-500 mx-auto mb-4" size={48} />
          <p className="text-zinc-500 font-bold">Loading DJ profile...</p>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !dj) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" data-testid="error-state">
        <div className="text-center max-w-md">
          <div className="w-24 h-24 rounded-full bg-red-900/20 border border-red-800/50 flex items-center justify-center mx-auto mb-6">
            <Music className="text-red-500" size={32} />
          </div>
          <h1 className="text-3xl font-black text-white uppercase mb-2">DJ Not Found</h1>
          <p className="text-zinc-500 font-bold mb-6">{error || "This DJ profile doesn't exist or hasn't been approved."}</p>
          <Link href="/explore">
            <Button>Explore All DJs</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-24" data-testid="dj-profile-page">
      {/* Hero Banner */}
      <div
        className="relative h-[400px] bg-gradient-to-b from-zinc-900 to-black"
        style={{
          backgroundImage: dj.banner_url ? `url(${dj.banner_url})` : undefined,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-transparent" />
        
        <div className="absolute bottom-0 left-0 right-0 px-6 md:px-12 pb-8">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
                {dj.dj_name}
              </h1>
              
              {dj.genres && dj.genres.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {dj.genres.filter(g => g).map((genre, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-full bg-violet-600/20 border border-violet-500/30 text-violet-400 text-xs font-black uppercase tracking-wider"
                    >
                      {genre}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 md:px-12 mt-12">
        <div className="max-w-7xl mx-auto">
          
          {/* Bio Section */}
          {dj.bio && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-16"
            >
              <div className="p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800">
                <h2 className="text-xl font-black text-white uppercase italic tracking-tight mb-4">About</h2>
                <p className="text-zinc-400 leading-relaxed">{dj.bio}</p>
              </div>
            </motion.div>
          )}

          {/* Tracks Section */}
          {tracks.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="mb-16"
            >
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <Music className="text-violet-500" size={28} />
                  <h2 className="text-3xl font-black text-white uppercase italic tracking-tight">
                    Tracks ({tracks.length})
                  </h2>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="tracks-section">
                {tracks.map((track) => (
                  <TrackCard
                    key={track.id}
                    id={track.id}
                    title={track.title}
                    price={track.price}
                    djName={dj.dj_name}
                    djSlug={dj.slug}
                    youtubeUrl={track.youtube_url}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* Albums Section */}
          {albums.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mb-16"
            >
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <Package className="text-amber-500" size={28} />
                  <h2 className="text-3xl font-black text-white uppercase italic tracking-tight">
                    Album Packs ({albums.length})
                  </h2>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="albums-section">
                {albums.map((album) => (
                  <AlbumCard
                    key={album.id}
                    id={album.id}
                    title={album.title}
                    description={album.description}
                    price={album.price}
                    fileSize={album.file_size}
                    djName={dj.dj_name}
                    djSlug={dj.slug}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* Empty State */}
          {tracks.length === 0 && albums.length === 0 && (
            <div className="text-center py-24">
              <Music className="text-zinc-700 mx-auto mb-4" size={64} />
              <h3 className="text-2xl font-black text-white uppercase mb-2">No Content Yet</h3>
              <p className="text-zinc-500 font-bold">This DJ hasn't uploaded any tracks or albums yet.</p>
            </div>
          )}

          {/* Subscribe CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="p-8 md:p-12 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-700 text-center"
          >
            <Users className="text-white/80 mx-auto mb-4" size={48} />
            <h3 className="text-3xl font-black text-white uppercase italic tracking-tight mb-4">
              Subscribe to {dj.dj_name}
            </h3>
            <p className="text-white/80 font-bold mb-6 max-w-xl mx-auto">
              Get monthly access to tracks and exclusive content with a DJ subscription.
            </p>
            <Link href="/pricing">
              <Button size="lg" className="bg-white text-violet-700 hover:bg-zinc-100 px-12">
                View Plans
              </Button>
            </Link>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
