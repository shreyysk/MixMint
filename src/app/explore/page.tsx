'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { DJCard } from "@/components/ui/DJCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Search, Users, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface DJ {
  id: string;
  user_id: string;
  dj_name: string;
  slug: string;
  bio: string | null;
  genres: string[] | null;
  profile_picture_url: string | null;
  status: string;
  location: string | null;
  popularity_score: number;
  created_at: string;
}

export default function ExplorePage() {
  const [djs, setDjs] = useState<DJ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'newest' | 'popularity'>('newest');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    loadDJs();
  }, []);

  async function loadDJs() {
    try {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from('dj_profiles')
        .select('*')
        .eq('status', 'approved')
        .order('created_at', { ascending: false });

      if (fetchError) throw fetchError;

      setDjs(data || []);
    } catch (err: any) {
      console.error('[EXPLORE_ERROR]', err);
      setError(err.message || 'Failed to load DJs');
    } finally {
      setLoading(false);
    }
  }

  const allGenres = ['All', ...Array.from(new Set(djs.flatMap(dj => dj.genres || []))).sort()];

  const filteredDJs = djs
    .filter(dj => {
      // 1. Search Query
      const matchesSearch = !searchQuery || [
        dj.dj_name,
        dj.bio,
        ...(dj.genres || []),
        dj.location
      ].some(text => text?.toLowerCase().includes(searchQuery.toLowerCase()));

      // 2. Genre Filter
      const matchesGenre = selectedGenre === 'All' || dj.genres?.includes(selectedGenre);

      return matchesSearch && matchesGenre;
    })
    .sort((a, b) => {
      if (sortBy === 'popularity') return b.popularity_score - a.popularity_score;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  return (
    <div className="min-h-screen pb-24" data-testid="explore-page">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-purple-primary/10 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-purple-primary/20 rounded-full blur-[120px] pointer-events-none" />

        <div className="relative px-6 md:px-12 pt-8 pb-12">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              className="flex flex-col lg:flex-row lg:items-end justify-between gap-8"
            >
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-primary/10 border border-purple-primary/20 mb-4">
                  <Sparkles size={14} className="text-purple-primary" />
                  <span className="text-xs font-medium text-purple-primary-dark">Discover Amazing Artists</span>
                </div>
                <h1 className="text-4xl md:text-5xl font-heading font-bold text-white mb-3">
                  Explore <span className="text-gradient-purple">DJs</span>
                </h1>
                <p className="text-zinc-500 max-w-lg">
                  Discover artists pushing the boundaries.{' '}
                  {djs.length > 0 && (
                    <span className="text-mint-accent font-medium">{djs.length} artists available.</span>
                  )}
                </p>
              </div>

              {/* Search */}
              <div className="relative group w-full lg:w-auto">
                <div className="absolute inset-0 bg-purple-primary/20 rounded-2xl blur-xl opacity-0 group-focus-within:opacity-50 transition-opacity" />
                <Search
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-purple-primary transition-colors z-10"
                  size={18}
                />
                <input
                  type="text"
                  placeholder="Search DJs, genres..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="relative w-full lg:w-80 glass border border-white/5 rounded-2xl pl-11 pr-4 py-3.5 text-sm focus:outline-none focus:border-purple-primary/50 transition-all placeholder:text-zinc-600"
                  data-testid="dj-search-input"
                />
              </div>
            </motion.div>

            {/* Filters & Sorting */}
            <motion.div
              initial={mounted ? { opacity: 0, y: 10 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.1 }}
              className="mt-8 flex flex-wrap items-center gap-4 lg:gap-6"
            >
              {/* Genre Filter */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black text-zinc-600 uppercase tracking-widest leading-none">Genre</span>
                <select
                  value={selectedGenre}
                  onChange={(e) => setSelectedGenre(e.target.value)}
                  className="bg-zinc-900/50 border border-white/5 rounded-xl px-4 py-2 text-xs font-bold text-zinc-300 focus:outline-none focus:border-purple-primary transition-all cursor-pointer"
                >
                  {allGenres.map(genre => (
                    <option key={genre} value={genre}>{genre}</option>
                  ))}
                </select>
              </div>

              {/* Sort By */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black text-zinc-600 uppercase tracking-widest leading-none">Sort By</span>
                <div className="flex p-1 bg-zinc-900/50 border border-white/5 rounded-xl">
                  <button
                    onClick={() => setSortBy('newest')}
                    className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-tighter transition-all ${sortBy === 'newest' ? 'bg-purple-primary text-white shadow-purple-glow' : 'text-zinc-500 hover:text-zinc-300'
                      }`}
                  >
                    Newest
                  </button>
                  <button
                    onClick={() => setSortBy('popularity')}
                    className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-tighter transition-all ${sortBy === 'popularity' ? 'bg-purple-primary text-white shadow-purple-glow' : 'text-zinc-500 hover:text-zinc-300'
                      }`}
                  >
                    Popularity
                  </button>
                </div>
              </div>

              <div className="flex-1" />

              <div className="text-[10px] font-black text-zinc-600 uppercase tracking-widest">
                Showing {filteredDJs.length} results
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Loading State */}
          {loading && (
            <div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
              data-testid="loading-state"
            >
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-surface-dark rounded-2xl overflow-hidden animate-pulse">
                  <div className="aspect-square bg-zinc-800" />
                  <div className="p-4">
                    <div className="w-3/4 h-5 bg-zinc-800 rounded-lg mb-2" />
                    <div className="flex gap-2">
                      <div className="w-16 h-4 bg-zinc-800 rounded-full" />
                      <div className="w-12 h-4 bg-zinc-800 rounded-full" />
                    </div>
                  </div>
                </div>
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
                title="Failed to load DJs"
                message={error}
                action={{
                  label: 'Try Again',
                  onClick: loadDJs,
                }}
                variant="error"
              />
            </motion.div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredDJs.length === 0 && (
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
              data-testid="empty-state"
            >
              <EmptyState
                icon={<Users size={40} className="text-purple-primary" />}
                title="No DJs Found"
                description={
                  searchQuery
                    ? `No results for "${searchQuery}". Try a different search term.`
                    : 'No approved DJs yet. Check back soon for amazing DJ content!'
                }
              />
            </motion.div>
          )}

          {/* DJ Grid */}
          {!loading && !error && filteredDJs.length > 0 && (
            <motion.div
              initial={mounted ? { opacity: 0 } : false}
              animate={mounted ? { opacity: 1 } : {}}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
              data-testid="dj-grid"
            >
              {filteredDJs.map((dj, index) => (
                <motion.div
                  key={dj.id}
                  initial={mounted ? { opacity: 0, y: 20 } : false}
                  animate={mounted ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: index * 0.05 }}
                >
                  <DJCard
                    name={dj.dj_name}
                    slug={dj.slug}
                    genre={dj.genres || []}
                    image={dj.profile_picture_url}
                  />
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
