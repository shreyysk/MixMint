"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { supabase } from "@/app/lib/supabaseClient";
import { TrackCard } from "@/app/components/ui/TrackCard";
import { AlbumCard } from "@/app/components/ui/AlbumCard";
import { Button } from "@/app/components/ui/Button";
import { Loader2, Music, Package, Users, ArrowRight } from "lucide-react";
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

      const { data: djData, error: djError } = await supabase
        .from("dj_profiles")
        .select("*")
        .eq("slug", slug)
        .eq("status", "approved")
        .single();

      if (djError) throw new Error("DJ not found");
      if (!djData) throw new Error("DJ not found");

      setDJ(djData);

      const { data: tracksData } = await supabase
        .from("tracks")
        .select("id, title, price, youtube_url")
        .eq("dj_id", djData.id)
        .eq("status", "active")
        .order("created_at", { ascending: false });

      setTracks(tracksData || []);

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
          <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center mx-auto mb-6">
            <Loader2 className="animate-spin text-violet-400" size={28} />
          </div>
          <p className="text-zinc-500">Loading DJ profile...</p>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !dj) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" data-testid="error-state">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 rounded-2xl bg-red-900/10 border border-red-800/30 flex items-center justify-center mx-auto mb-6">
            <Music className="text-red-400" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">DJ Not Found</h1>
          <p className="text-zinc-500 mb-6">{error || "This DJ profile doesn't exist or hasn't been approved."}</p>
          <Link href="/explore">
            <Button>Explore All DJs</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-24" data-testid="dj-profile-page">
      {/* Hero Banner */}
      <div
        className="relative h-[350px] md:h-[400px]"
        style={{
          backgroundImage: dj.banner_url ? `url(${dj.banner_url})` : undefined,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#09090B] via-[#09090B]/80 to-transparent" />
        
        {/* Content */}
        <div className="absolute bottom-0 left-0 right-0 px-6 md:px-12 pb-10">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {/* Genres */}
              {dj.genres && dj.genres.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {dj.genres.filter(g => g).map((genre, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 text-xs font-medium"
                    >
                      {genre}
                    </span>
                  ))}
                </div>
              )}
              
              {/* DJ Name */}
              <h1 className="text-4xl md:text-6xl font-bold text-white mb-2">
                {dj.dj_name}
              </h1>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 md:px-12 mt-10">
        <div className="max-w-7xl mx-auto">
          
          {/* Bio Section */}
          {dj.bio && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-16"
            >
              <div className="p-6 md:p-8 rounded-2xl bg-zinc-900/50 border border-zinc-800/60">
                <h2 className="text-lg font-semibold text-white mb-3">About</h2>
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
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center">
                  <Music className="text-violet-400" size={18} />
                </div>
                <h2 className="text-2xl font-bold text-white">
                  Tracks <span className="text-zinc-500 text-lg font-normal">({tracks.length})</span>
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5" data-testid="tracks-section">
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
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-amber-600/10 border border-amber-500/20 flex items-center justify-center">
                  <Package className="text-amber-400" size={18} />
                </div>
                <h2 className="text-2xl font-bold text-white">
                  Album Packs <span className="text-zinc-500 text-lg font-normal">({albums.length})</span>
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5" data-testid="albums-section">
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
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-20"
            >
              <div className="w-20 h-20 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-center mx-auto mb-6">
                <Music className="text-zinc-600" size={32} />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No Content Yet</h3>
              <p className="text-zinc-500">This DJ hasn't uploaded any tracks or albums yet.</p>
            </motion.div>
          )}

          {/* Subscribe CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="relative p-8 md:p-12 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-700 overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute -bottom-10 -right-10 w-60 h-60 bg-white/10 blur-[80px] rounded-full pointer-events-none" />
            
            <div className="relative flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="text-center md:text-left">
                <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center mb-5 mx-auto md:mx-0">
                  <Users className="text-white" size={24} />
                </div>
                <h3 className="text-2xl md:text-3xl font-bold text-white mb-3">
                  Subscribe to {dj.dj_name}
                </h3>
                <p className="text-white/70 max-w-md">
                  Get monthly access to tracks and exclusive content with a DJ subscription.
                </p>
              </div>
              <Link href="/pricing">
                <Button size="lg" className="bg-white text-violet-700 hover:bg-zinc-100 px-8 shrink-0">
                  View Plans
                  <ArrowRight size={18} />
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
