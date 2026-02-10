"use client";

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { TrackCard } from '@/components/ui/TrackCard';
import { TrackCardSkeleton } from '@/components/ui/TrackCardSkeleton';
import { useSearch } from './context/SearchContext';
import { DJCard } from '@/components/ui/DJCard';
import { motion } from 'framer-motion';
import { Sparkles, TrendingUp, Users } from 'lucide-react';
import { Hero } from '@/components/features/landing/Hero';

export default function Home() {
  const { searchTerm } = useSearch();
  const [tracks, setTracks] = useState<any[]>([]);
  const [featuredDJs, setFeaturedDJs] = useState<any[]>([]);
  const [trendingTracks, setTrendingTracks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHomeContent() {
      try {
        setLoading(true);

        // 1. Fetch Latest Tracks
        const { data: latestTracks } = await supabase
          .from('tracks')
          .select(`
            *,
            dj_profiles (dj_name, slug)
          `)
          .order('created_at', { ascending: false })
          .limit(4);

        // 2. Fetch Featured DJs (by popularity)
        const { data: featured } = await supabase
          .from('dj_profiles')
          .select('*')
          .eq('status', 'approved')
          .order('popularity_score', { ascending: false })
          .limit(5);

        // 3. Fetch Trending Tracks (simulated by high price or random for now)
        const { data: trending } = await supabase
          .from('tracks')
          .select('*, dj_profiles(dj_name, slug)')
          .order('id', { ascending: false }) // Just a different order for variety
          .limit(4);

        setTracks(latestTracks || []);
        setFeaturedDJs(featured || []);
        setTrendingTracks(trending || []);
      } catch (err) {
        console.error("Home content fetch failed:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchHomeContent();
  }, []);

  const filteredTracks = tracks.filter((track) =>
    track.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    track.djName?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="pb-24">
      <Hero />
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-12 space-y-24">
        {/* Featured DJs Carousel-like Section */}
        <section>
          <div className="flex items-center justify-between mb-10">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-primary/10 border border-purple-primary/20 mb-3">
                <Sparkles size={12} className="text-purple-primary" />
                <span className="text-[10px] font-black text-purple-primary uppercase tracking-[0.2em]">Featured Artists</span>
              </div>
              <h2 className="text-4xl font-black text-white uppercase italic tracking-tighter">On The <span className="text-gradient-purple">Rise</span></h2>
            </div>
          </div>

          <div className="flex gap-6 overflow-x-auto pb-8 scrollbar-hide -mx-6 px-6">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="min-w-[280px] h-40 bg-zinc-900 rounded-2xl animate-pulse" />
              ))
            ) : featuredDJs.map((dj) => (
              <div key={dj.id} className="min-w-[280px]">
                <DJCard
                  name={dj.dj_name}
                  slug={dj.slug}
                  genre={dj.genres || []}
                  image={dj.profile_picture_url}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Latest Releases */}
        <section>
          <div className="flex items-center justify-between mb-10">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-mint-accent/10 border border-mint-accent/20 mb-3">
                <Users size={12} className="text-mint-accent" />
                <span className="text-[10px] font-black text-mint-accent uppercase tracking-[0.2em]">Fresh Content</span>
              </div>
              <h2 className="text-4xl font-black text-white uppercase italic tracking-tighter">Latest <span className="text-gradient-mint">Drops</span></h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TrackCardSkeleton key={i} />
              ))
            ) : tracks.map((track) => (
              <TrackCard
                key={track.id}
                id={track.id}
                title={track.title}
                djName={track.dj_profiles?.dj_name}
                djSlug={track.dj_profiles?.slug}
                price={track.price}
                bpm={track.bpm}
                genre={track.genre}
              />
            ))}
          </div>
        </section>

        {/* Trending Section */}
        <section className="bg-zinc-900/30 -mx-6 sm:-mx-12 px-6 sm:px-12 py-16 rounded-[3rem] border border-white/5">
          <div className="flex flex-col lg:flex-row gap-12">
            <div className="lg:w-1/3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 mb-4">
                <TrendingUp size={12} className="text-orange-500" />
                <span className="text-[10px] font-black text-orange-500 uppercase tracking-[0.2em]">High Demand</span>
              </div>
              <h2 className="text-5xl font-black text-white uppercase italic tracking-tighter mb-6">Trending <br /> <span className="text-orange-gradient">Now</span></h2>
              <p className="text-zinc-500 font-bold leading-relaxed">
                These tracks are dominating the community. Join the conversation and add them to your collection.
              </p>
            </div>

            <div className="lg:w-2/3 grid grid-cols-1 sm:grid-cols-2 gap-6">
              {trendingTracks.map((track, index) => (
                <motion.div
                  key={track.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <TrackCard
                    id={track.id}
                    title={track.title}
                    djName={track.dj_profiles?.dj_name}
                    djSlug={track.dj_profiles?.slug}
                    price={track.price}
                    bpm={track.bpm}
                    genre={track.genre}
                    className="!bg-zinc-950/50"
                  />
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
