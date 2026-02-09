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
}

export default function ExplorePage() {
  const [djs, setDjs] = useState<DJ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
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

  const filteredDJs = djs.filter(dj => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      dj.dj_name.toLowerCase().includes(query) ||
      dj.bio?.toLowerCase().includes(query) ||
      dj.genres?.some(g => g.toLowerCase().includes(query))
    );
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
