"use client";

import React, { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { DJCard } from "@/app/components/ui/DJCard";
import { Search, Loader2, Users } from "lucide-react";
import { motion } from "framer-motion";

interface DJ {
  id: string;
  user_id: string;
  dj_name: string;
  slug: string;
  bio: string | null;
  genres: string[] | null;
  banner_url: string | null;
  status: string;
}

export default function ExplorePage() {
  const [djs, setDjs] = useState<DJ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadDJs();
  }, []);

  async function loadDJs() {
    try {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from("dj_profiles")
        .select("*")
        .eq("status", "approved")
        .order("created_at", { ascending: false });

      if (fetchError) throw fetchError;

      setDjs(data || []);
    } catch (err: any) {
      console.error("[EXPLORE_ERROR]", err);
      setError(err.message || "Failed to load DJs");
    } finally {
      setLoading(false);
    }
  }

  // Filter DJs based on search
  const filteredDJs = djs.filter((dj) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      dj.dj_name.toLowerCase().includes(query) ||
      dj.bio?.toLowerCase().includes(query) ||
      dj.genres?.some((g) => g.toLowerCase().includes(query))
    );
  });

  return (
    <div className="min-h-screen pb-24" data-testid="explore-page">
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
                Explore <span className="text-violet-gradient">DJs</span>
              </h1>
              <p className="text-zinc-500 max-w-lg">
                Discover artists pushing the boundaries. {djs.length > 0 && `${djs.length} artists available.`}
              </p>
            </div>

            {/* Search */}
            <div className="relative group w-full lg:w-auto">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-violet-400 transition-colors" size={18} />
              <input
                type="text"
                placeholder="Search DJs, genres..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full lg:w-72 bg-zinc-900/60 border border-zinc-800/60 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-zinc-600"
                data-testid="dj-search-input"
              />
            </div>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-32" data-testid="loading-state">
              <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center mb-6">
                <Loader2 className="animate-spin text-violet-400" size={28} />
              </div>
              <p className="text-zinc-500">Loading artists...</p>
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
              <p className="text-red-400 font-medium mb-2">Failed to load DJs</p>
              <p className="text-red-500/60 text-sm mb-4">{error}</p>
              <button
                onClick={loadDJs}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-500 rounded-xl text-white font-medium text-sm transition-colors"
              >
                Try Again
              </button>
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredDJs.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-32" 
              data-testid="empty-state"
            >
              <div className="w-20 h-20 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-center mx-auto mb-6">
                <Users className="text-zinc-600" size={32} />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No DJs Found</h3>
              <p className="text-zinc-500">
                {searchQuery ? `No results for "${searchQuery}"` : "No approved DJs yet. Check back soon!"}
              </p>
            </motion.div>
          )}

          {/* DJ Grid */}
          {!loading && !error && filteredDJs.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
              data-testid="dj-grid"
            >
              {filteredDJs.map((dj) => (
                <DJCard
                  key={dj.id}
                  name={dj.dj_name}
                  slug={dj.slug}
                  genre={dj.genres || []}
                  image={dj.banner_url || `https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=400&h=500&auto=format&fit=crop`}
                />
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
