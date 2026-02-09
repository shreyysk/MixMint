'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/app/lib/supabaseClient';
import { DJCard } from '@/app/components/ui/DJCard';
import { TrackCard } from '@/app/components/ui/TrackCard';
import { AlbumCard } from '@/app/components/ui/AlbumCard';
import { Button } from '@/app/components/ui/Button';
import Link from 'next/link';
import { ChevronRight, Music, ArrowRight, Sparkles, Package } from 'lucide-react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';

interface DJ {
  id: string;
  dj_name: string;
  slug: string;
  genre: string[];
  profile_picture_url: string;
}

interface Track {
  id: string;
  title: string;
  price: number;
  youtube_url: string | null;
  dj_id: string;
  dj_profile?: {
    dj_name: string;
    slug: string;
  };
}

interface Album {
    id: string;
    title: string;
    price: number;
    dj_profile?: {
        dj_name: string,
        slug: string
    },
    trackCount: number;
}

export function Home() {
  const [featuredDJs, setFeaturedDJs] = useState<DJ[]>([]);
  const [latestTracks, setLatestTracks] = useState<Track[]>([]);
  const [featuredAlbums, setFeaturedAlbums] = useState<Album[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function fetchData() {
      const { data: djs } = await supabase
        .from('dj_profiles')
        .select('id, dj_name, slug, genre, profile_picture_url')
        .eq('featured', true)
        .limit(6);

      const { data: tracks } = await supabase
        .from('tracks')
        .select(
          `
                    id,
                    title,
                    price,
                    youtube_url,
                    dj_id,
                    dj_profiles:dj_id (
                        dj_name,
                        slug
                    )
                `
        )
        .order('created_at', { ascending: false })
        .limit(4);

      const { data: albumsData } = await supabase
        .from('albums')
        .select(
          `
            id,
            title,
            price,
            dj_profiles:dj_id (
                dj_name,
                slug
            ),
            tracks (
                id
            )
        `
        )
        .order('created_at', { ascending: false })
        .limit(4);

      const transformedTracks = (tracks || []).map((track: any) => ({
        ...track,
        dj_profile: Array.isArray(track.dj_profiles)
          ? track.dj_profiles[0]
          : track.dj_profiles,
      }));

      const transformedAlbums = (albumsData || []).map((album: any) => ({
        id: album.id,
        title: album.title,
        price: album.price,
        dj_profile: Array.isArray(album.dj_profiles)
            ? album.dj_profiles[0]
            : album.dj_profiles,
        trackCount: album.tracks?.length || 0,
    }));

      setFeaturedDJs(djs || []);
      setLatestTracks(transformedTracks || []);
      setFeaturedAlbums(transformedAlbums);
      setLoading(false);
    }

    fetchData();
  }, []);

  const handlePurchase = (type: 'track' | 'album', id: string) => {
    router.push(`/${type}/${id}`); // Navigate to detail page for purchase
  };

  return (
    <div className="flex flex-col pb-24">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center px-6 md:px-12 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute top-[15%] right-[-15%] w-[600px] h-[600px] bg-violet-600/8 blur-[180px] rounded-full pointer-events-none" />
        <div className="absolute bottom-[10%] left-[-10%] w-[500px] h-[500px] bg-blue-600/5 blur-[150px] rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto w-full">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
            className="max-w-3xl"
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-medium mb-8">
              <Sparkles size={14} />
              <span>Direct Artist Support Platform</span>
            </div>

            {/* Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white leading-[1.1] tracking-tight mb-6">
              MixMint —{' '}
              <span className="text-violet-gradient">Home of DJ</span>{' '}
              Releases
            </h1>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-zinc-400 max-w-xl mb-10 leading-relaxed">
              Buy tracks, subscribe to DJs, and access exclusive drops —{' '}
              <span className="text-zinc-200">
                without the noise of streaming.
              </span>
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap gap-4">
              <Link href="/explore">
                <Button size="lg" className="px-8">
                  Explore DJs
                  <ChevronRight size={18} />
                </Button>
              </Link>
              <Link href="/dj/apply">
                <Button variant="outline" size="lg" className="px-8">
                  Become a DJ
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
      {/* Featured DJs Section */}
      <section className="px-6 md:px-12 py-16">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-3">
                Featured Artists
              </h2>
              <p className="text-zinc-500 max-w-lg">
                Hand-picked legends and rising stars from the scene.
              </p>
            </div>
            <Link href="/explore">
              <Button variant="ghost" className="group">
                View All
                <ChevronRight
                  size={16}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </Button>
            </Link>
          </div>

          {/* DJ Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {featuredDJs.map(dj => (
              <DJCard
                key={dj.slug}
                name={dj.dj_name}
                slug={dj.slug}
                genre={dj.genre}
                image={dj.profile_picture_url}
              />
            ))}
          </div>
        </div>
      </section>
      
      {/* Featured Albums Section */}
      <section className="px-6 md:px-12 py-16 bg-zinc-950/50">
          <div className="max-w-7xl mx-auto">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
                  <div>
                      <h2 className="text-3xl md:text-4xl font-bold text-white mb-3">Featured Albums</h2>
                      <p className="text-zinc-500 max-w-lg">Curated collections and special releases from our DJs.</p>
                  </div>
                  <Link href="/albums">
                      <Button variant="ghost" className="group">
                          View All
                          <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                      </Button>
                  </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                  {featuredAlbums.map(album => (
                      <AlbumCard
                          key={album.id}
                          id={album.id}
                          title={album.title}
                          djName={album.dj_profile?.dj_name}
                          djSlug={album.dj_profile?.slug}
                          price={album.price}
                          trackCount={album.trackCount}
                          onPurchase={() => handlePurchase('album', album.id)}
                      />
                  ))}
              </div>
          </div>
      </section>

      {/* Latest Tracks Section */}
      <section className="px-6 md:px-12 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-3">
                Latest Tracks
              </h2>
              <p className="text-zinc-500 max-w-lg">
                The freshest drops from our community.
              </p>
            </div>
            <Link href="/tracks">
              <Button variant="ghost" className="group">
                View All
                <ChevronRight
                  size={16}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </Button>
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {latestTracks.map(track => (
              <TrackCard
                key={track.id}
                id={track.id}
                title={track.title}
                djName={track.dj_profile?.dj_name}
                djSlug={track.dj_profile?.slug}
                youtube_url={track.youtube_url}
                price={track.price}
                onPurchase={() => handlePurchase('track', track.id)}
              />
            ))}
          </div>
        </div>
      </section>
      {/* CTA Section */}
      <section className="px-6 md:px-12 py-24">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative p-10 md:p-16 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-700 text-center overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-white/10 blur-[100px] rounded-full pointer-events-none" />

            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 max-w-2xl mx-auto leading-tight">
              Ready to claim your sound?
            </h2>
            <p className="text-white/80 text-lg max-w-xl mx-auto mb-10">
              Join listeners supporting artists directly. No subscription
              required to start.
            </p>
            <Link href="/auth/signup">
              <Button
                size="lg"
                className="bg-white text-violet-700 hover:bg-zinc-100 px-10"
              >
                Get Started
                <ArrowRight size={18} />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
