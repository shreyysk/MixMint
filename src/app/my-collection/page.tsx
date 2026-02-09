'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { EmptyState } from "@/components/ui/EmptyState";
import { Loader2, Music, Disc3, Library, Sparkles } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { CollectionItemCard } from "@/components/ui/CollectionItemCard";
import { motion } from 'framer-motion';

interface CollectionItem {
  id: string;
  title: string;
  type: 'track' | 'album';
  file_path?: string;
  djName?: string;
  djSlug?: string;
}

export default function MyCollectionPage() {
  const { user } = useAuth();
  const [collection, setCollection] = useState<CollectionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (user) {
      fetchCollection();
    }
  }, [user]);

  async function fetchCollection() {
    if (!user) return;
    setLoading(true);

    try {
      const { data: purchases, error: purchaseErr } = await supabase
        .from('purchases')
        .select('content_id, content_type')
        .eq('user_id', user.id);

      if (purchaseErr) throw purchaseErr;

      const trackIds = purchases.filter(p => p.content_type === 'track').map(p => p.content_id);
      const albumIds = purchases.filter(p => p.content_type === 'zip').map(p => p.content_id);

      let tracksData: any[] = [];
      if (trackIds.length > 0) {
        const { data, error } = await supabase
          .from('tracks')
          .select('id, title, dj_profiles(dj_name, slug)')
          .in('id', trackIds);
        if (error) console.error("Tracks fetch error:", error);
        else tracksData = data || [];
      }

      let albumsData: any[] = [];
      if (albumIds.length > 0) {
        const { data, error } = await supabase
          .from('album_packs')
          .select('id, title, dj_profiles(dj_name, slug)')
          .in('id', albumIds);
        if (error) console.error("Albums fetch error:", error);
        else albumsData = data || [];
      }

      const transformed: CollectionItem[] = [
        ...tracksData.map(t => ({
          id: t.id,
          title: t.title,
          type: 'track' as const,
          djName: t.dj_profiles?.dj_name,
          djSlug: t.dj_profiles?.slug,
        })),
        ...albumsData.map(a => ({
          id: a.id,
          title: a.title,
          type: 'album' as const,
          djName: a.dj_profiles?.dj_name,
          djSlug: a.dj_profiles?.slug,
        }))
      ];

      setCollection(transformed);
    } catch (err: any) {
      console.error('Error fetching collection:', err);
    } finally {
      setLoading(false);
    }
  }

  const handleDownload = async (itemType: 'track' | 'album', itemId: string) => {
    setDownloading(itemId);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        alert("Please log in to download.");
        return;
      }

      const res = await fetch("/api/download-token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          content_id: itemId,
          content_type: itemType === 'track' ? 'track' : 'zip'
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Download failed");
      }

      window.location.href = `/api/download?token=${data.token}`;
    } catch (error: any) {
      console.error('Download error:', error);
      alert(error.message || "Failed to initiate download");
    } finally {
      setDownloading(null);
    }
  };

  const tracks = collection.filter(item => item.type === 'track');
  const albums = collection.filter(item => item.type === 'album');

  return (
    <div className="min-h-screen pb-24">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-mint-accent/10 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-0 right-0 w-[600px] h-[400px] bg-mint-accent/20 rounded-full blur-[120px] pointer-events-none" />

        <div className="relative px-6 md:px-12 pt-8 pb-12">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={mounted ? { opacity: 0, y: 20 } : false}
              animate={mounted ? { opacity: 1, y: 0 } : {}}
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-mint-accent/10 border border-mint-accent/20 mb-4">
                <Library size={14} className="text-mint-accent" />
                <span className="text-xs font-medium text-mint-accent">Your Music Library</span>
              </div>
              <h1 className="text-4xl md:text-5xl font-heading font-bold text-white mb-3">
                My <span className="text-gradient-mint">Collection</span>
              </h1>
              <p className="text-zinc-500 max-w-lg">
                All your purchased tracks and albums in one place.
                {collection.length > 0 && (
                  <span className="text-mint-accent font-medium"> {collection.length} items owned.</span>
                )}
              </p>
            </motion.div>
          </div>
        </div>
      </div>

      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-surface-dark rounded-2xl overflow-hidden animate-pulse">
                  <div className="aspect-square bg-zinc-800" />
                  <div className="p-4">
                    <div className="w-3/4 h-5 bg-zinc-800 rounded-lg mb-2" />
                    <div className="w-1/2 h-4 bg-zinc-800 rounded-lg" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Tabs defaultValue="tracks">
              <TabsList className="mb-8 bg-surface-dark border border-white/5 p-1 rounded-xl">
                <TabsTrigger
                  value="tracks"
                  className="data-[state=active]:bg-purple-primary data-[state=active]:text-white"
                >
                  <Music size={16} className="mr-2" />
                  Tracks ({tracks.length})
                </TabsTrigger>
                <TabsTrigger
                  value="albums"
                  className="data-[state=active]:bg-mint-accent data-[state=active]:text-black"
                >
                  <Disc3 size={16} className="mr-2" />
                  Albums ({albums.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="tracks">
                {tracks.length > 0 ? (
                  <motion.div
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
                    initial={mounted ? { opacity: 0 } : false}
                    animate={mounted ? { opacity: 1 } : {}}
                  >
                    {tracks.map((track, index) => (
                      <motion.div
                        key={track.id}
                        initial={mounted ? { opacity: 0, y: 20 } : false}
                        animate={mounted ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: index * 0.05 }}
                      >
                        <CollectionItemCard
                          item={track}
                          onDownload={handleDownload}
                          isLoading={downloading === track.id}
                        />
                      </motion.div>
                    ))}
                  </motion.div>
                ) : (
                  <EmptyState
                    icon={<Music size={40} className="text-purple-primary" />}
                    title="No Tracks Yet"
                    description="Purchased tracks will appear here. Explore DJs to find your next favorite track!"
                  />
                )}
              </TabsContent>

              <TabsContent value="albums">
                {albums.length > 0 ? (
                  <motion.div
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
                    initial={mounted ? { opacity: 0 } : false}
                    animate={mounted ? { opacity: 1 } : {}}
                  >
                    {albums.map((album, index) => (
                      <motion.div
                        key={album.id}
                        initial={mounted ? { opacity: 0, y: 20 } : false}
                        animate={mounted ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: index * 0.05 }}
                      >
                        <CollectionItemCard
                          item={album}
                          onDownload={handleDownload}
                          isLoading={downloading === album.id}
                        />
                      </motion.div>
                    ))}
                  </motion.div>
                ) : (
                  <EmptyState
                    icon={<Disc3 size={40} className="text-mint-accent" />}
                    title="No Albums Yet"
                    description="Purchased album packs will appear here. Bundle tracks for better value!"
                  />
                )}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  );
}
