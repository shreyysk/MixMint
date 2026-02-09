'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/app/lib/supabaseClient';
import { useAuth } from '@/app/lib/AuthContext';
import { EmptyState } from '@/app/components/ui/EmptyState';
import { Loader2, Music, Package } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/Tabs';
import { CollectionItemCard } from '@/app/components/ui/CollectionItemCard';

interface CollectionItem {
  id: string;
  title: string;
  type: 'track' | 'album';
  file_path?: string; // Optional for albums
  djName?: string;
  djSlug?: string;
}

export default function MyCollectionPage() {
  const { user } = useAuth();
  const [collection, setCollection] = useState<CollectionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchCollection();
    }
  }, [user]);

  async function fetchCollection() {
    setLoading(true);

    const { data: sales, error } = await supabase
      .from('sales')
      .select(
        `
                item_type,
                track_id,
                album_id,
                tracks:track_id (id, title, file_path, dj_profiles:dj_id (dj_name, slug)),
                albums:album_id (id, title, dj_profiles:dj_id (dj_name, slug))
            `
      )
      .eq('user_id', user?.id);

    if (error) {
      console.error('Error fetching collection:', error);
      setLoading(false);
      return;
    }

    const items: CollectionItem[] = sales
      .map(sale => {
        if (sale.item_type === 'track' && sale.tracks) {
          return {
            id: sale.tracks.id,
            title: sale.tracks.title,
            type: 'track',
            file_path: sale.tracks.file_path,
            djName: sale.tracks.dj_profiles?.dj_name,
            djSlug: sale.tracks.dj_profiles?.slug,
          };
        }
        if (sale.item_type === 'album' && sale.albums) {
          return {
            id: sale.albums.id,
            title: sale.albums.title,
            type: 'album',
            djName: sale.albums.dj_profiles?.dj_name,
            djSlug: sale.albums.dj_profiles?.slug,
          };
        }
        return null;
      })
      .filter((item): item is CollectionItem => item !== null);

    setCollection(items);
    setLoading(false);
  }

  const handleDownload = async (itemType: 'track' | 'album', itemId: string) => {
    setDownloading(itemId);
    try {
      if (itemType === 'track') {
        const item = collection.find(i => i.id === itemId);
        if (!item || !item.file_path) throw new Error('Track file not found');

        const { data, error } = await supabase.storage.from('tracks').download(item.file_path);
        if (error) throw error;

        downloadBlob(data, `${item.title}.mp3`);

      } else if (itemType === 'album') {
        const { data, error } = await supabase.functions.invoke('download-album', {
            body: { albumId: itemId }
        });

        if (error) throw error;

        const item = collection.find(i => i.id === itemId);
        downloadBlob(new Blob([data]), `${item?.title || 'album'}.zip`, 'application/zip');
      }
    } catch (error: any) {
        console.error('Download error:', error.message);
        alert(`Error: ${error.message}`);
    } finally {
        setDownloading(null);
    }
  };

  const downloadBlob = (blob: Blob, filename: string, type?: string) => {
    const url = window.URL.createObjectURL(new Blob([blob], { type: type || 'application/octet-stream' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  const tracks = collection.filter(item => item.type === 'track');
  const albums = collection.filter(item => item.type === 'album');

  return (
    <div className="min-h-screen pb-24">
      <div className="px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-12">
            My Collection
          </h1>

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {Array.from({ length: 8 }).map((_, i) => (
                <CollectionItemCard key={i} item={{id: `${i}`, title: '', type: 'track'}} onDownload={() => {}} isLoading={true} />
              ))}
            </div>
          ) : (
            <Tabs defaultValue="tracks">
              <TabsList className="mb-8">
                <TabsTrigger value="tracks">Tracks ({tracks.length})</TabsTrigger>
                <TabsTrigger value="albums">Albums ({albums.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="tracks">
                {tracks.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                    {tracks.map(track => (
                      <CollectionItemCard
                        key={track.id}
                        item={track}
                        onDownload={handleDownload}
                        isLoading={downloading === track.id}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Music size={32} />}
                    title="No Tracks Yet"
                    description="Purchased tracks will appear here."
                  />
                )}
              </TabsContent>
              <TabsContent value="albums">
                {albums.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                    {albums.map(album => (
                      <CollectionItemCard
                        key={album.id}
                        item={album}
                        onDownload={handleDownload}
                        isLoading={downloading === album.id}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Package size={32} />}
                    title="No Albums Yet"
                    description="Purchased albums will appear here."
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
