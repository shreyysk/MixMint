
"use client";

import { supabase } from "@/app/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/app/components/RequireRole";
import { Button } from "@/app/components/ui/Button";

export default function ContentModeration() {
  const [tracks, setTracks] = useState<any[]>([]);
  const [albums, setAlbums] = useState<any[]>([]);

  useEffect(() => {
    fetchContent();
  }, []);

  async function fetchContent() {
    const { data: tracksData } = await supabase.from("tracks").select("*");
    const { data: albumsData } = await supabase.from("album_packs").select("*");
    setTracks(tracksData || []);
    setAlbums(albumsData || []);
  }

  const disableContent = async (contentId: string, contentType: 'track' | 'album') => {
    const table = contentType === 'track' ? 'tracks' : 'album_packs';
    await supabase.from(table).update({ status: "disabled" }).eq("id", contentId);
    alert(`Content disabled`);
    fetchContent();
  };

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">Content Moderation</h1>

        <h2 className="text-xl font-bold mb-2">Tracks</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {tracks.map((track) => (
            <div key={track.id} className="border p-3 rounded-lg">
              <p className="font-bold">{track.title}</p>
              <p className="text-sm text-zinc-400">Status: {track.status}</p>
              <Button 
                onClick={() => disableContent(track.id, 'track')} 
                disabled={track.status === 'disabled'}
                variant="destructive"
                size="sm"
                className="mt-2"
              >
                Disable Track
              </Button>
            </div>
          ))}
        </div>

        <h2 className="text-xl font-bold mb-2">Albums</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {albums.map((album) => (
            <div key={album.id} className="border p-3 rounded-lg">
              <p className="font-bold">{album.title}</p>
              <p className="text-sm text-zinc-400">Status: {album.status}</p>
              <Button 
                onClick={() => disableContent(album.id, 'album')} 
                disabled={album.status === 'disabled'}
                variant="destructive"
                size="sm"
                className="mt-2"
              >
                Disable Album
              </Button>
            </div>
          ))}
        </div>
      </div>
    </RequireRole>
  );
}
