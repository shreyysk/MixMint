"use client";

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { TrackCard } from '@/components/ui/TrackCard';
import { TrackCardSkeleton } from '@/components/ui/TrackCardSkeleton';
import { useSearch } from './context/SearchContext';

export default function Home() {
  const { searchTerm } = useSearch();
  const [tracks, setTracks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLatestTracks() {
      try {
        setLoading(true);
        const { data, error } = await supabase
          .from('tracks')
          .select(`
            id,
            title,
            price,
            dj_profiles (
              dj_name,
              slug
            )
          `)
          .eq('status', 'active')
          .order('created_at', { ascending: false })
          .limit(8);

        if (error) throw error;

        const transformed = data?.map(t => ({
          id: t.id,
          title: t.title,
          price: t.price,
          djName: (t.dj_profiles as any)?.dj_name,
          djSlug: (t.dj_profiles as any)?.slug
        })) || [];

        setTracks(transformed);
      } catch (err) {
        console.error("Latest tracks fetch failed:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchLatestTracks();
  }, []);

  const filteredTracks = tracks.filter((track) =>
    track.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    track.djName?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="mb-12">
        <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
          Latest <span className="text-violet-gradient">Releases</span>
        </h1>
        <p className="text-zinc-500 font-bold max-w-lg">
          Fresh drops from the underground. Direct from the artists to your vault.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <TrackCardSkeleton key={i} />
          ))
        ) : filteredTracks.length > 0 ? (
          filteredTracks.map((track) => (
            <TrackCard
              key={track.id}
              id={track.id}
              title={track.title}
              djName={track.djName}
              djSlug={track.djSlug}
              price={track.price}
            />
          ))
        ) : (
          <p className="text-zinc-500 italic col-span-full">No tracks found.</p>
        )}
      </div>
    </div>
  );
}
