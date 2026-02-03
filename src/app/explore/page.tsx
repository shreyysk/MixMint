"use client";

import React, { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { DJCard } from "@/app/components/ui/DJCard";
import { Search, Filter, Loader2 } from "lucide-react";
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
    <div className="pb-24" data-testid="explore-page">
      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-16"
          >
            <div>
              <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
                Explore <span className="text-violet-gradient">DJs</span>
              </h1>
              <p className="text-zinc-500 font-bold max-w-lg">
                Discover the architects of the soundscape. {djs.length} approved artists pushing the boundaries.
              </p>
            </div>

            {/* Search */}
            <div className="flex items-center gap-3">
              <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-violet-500 transition-colors" size={18} />
                <input
                  type="text"
                  placeholder="Search DJs, genres..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl pl-12 pr-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 w-full md:w-64 transition-all"
                  data-testid="dj-search-input"
                />
              </div>
            </div>
          </motion.div>

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24" data-testid="loading-state">
              <Loader2 className="animate-spin text-violet-500 mb-4" size={48} />
              <p className="text-zinc-500 font-bold">Loading DJs...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-8 rounded-2xl bg-red-900/20 border border-red-800/50 text-center" data-testid="error-state">
              <p className="text-red-400 font-bold mb-2">Failed to load DJs</p>
              <p className="text-red-500/70 text-sm mb-4">{error}</p>
              <button
                onClick={loadDJs}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white font-bold text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredDJs.length === 0 && (
            <div className="text-center py-24" data-testid="empty-state">
              <div className="w-24 h-24 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto mb-6">
                <Search className="text-zinc-600" size={32} />
              </div>
              <h3 className="text-2xl font-black text-white uppercase mb-2">No DJs Found</h3>
              <p className="text-zinc-500 font-bold">
                {searchQuery ? `No results for "${searchQuery}"` : "No approved DJs yet."}
              </p>
            </div>
          )}

          {/* DJ Grid */}
          {!loading && !error && filteredDJs.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8"
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
