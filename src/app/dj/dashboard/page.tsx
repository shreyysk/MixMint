"use client";

import { useAuth } from "@/app/lib/AuthContext";
import { supabase } from "@/app/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/app/components/RequireRole";

export default function DJDashboard() {
  const { user } = useAuth();
  const [tracks, setTracks] = useState<any[]>([]);
  const [albumPacks, setAlbumPacks] = useState<any[]>([]);
  const [loadingItems, setLoadingItems] = useState(true);

  useEffect(() => {
    const loadContent = async () => {
      setLoadingItems(true);
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session?.access_token) {
        console.warn("No session token, skipping content fetch");
        setLoadingItems(false);
        return;
      }

      const res = await fetch("/api/dj/tracks", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      const json = await res.json();
      console.log("DJ content response:", json);

      setTracks(json.tracks || []);
      setAlbumPacks(json.albumPacks || []);
      setLoadingItems(false);
    };

    if (user) {
      loadContent();
    }
  }, [user]);

  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-3xl font-bold mb-8">DJ Dashboard</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* TRACKS SECTION */}
          <section>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span>🎵</span> Your Tracks
            </h2>
            {loadingItems && <p className="opacity-60">Loading tracks...</p>}
            {!loadingItems && tracks.length === 0 && (
              <p className="opacity-60">No tracks uploaded yet.</p>
            )}
            {tracks.map((t) => (
              <div key={t.id} className="bg-white/5 border border-white/10 p-3 mb-3 rounded-lg">
                <p className="font-semibold">{t.title}</p>
                <p className="text-sm text-purple-400">₹{t.price}</p>
                <p className="text-xs opacity-50 mt-1">
                  {new Date(t.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </section>

          {/* ALBUM PACKS SECTION */}
          <section>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span>📦</span> Album Packs (ZIP)
            </h2>
            {loadingItems && <p className="opacity-60">Loading packs...</p>}
            {!loadingItems && albumPacks.length === 0 && (
              <p className="opacity-60">No album packs uploaded yet.</p>
            )}
            {albumPacks.map((p) => (
              <div key={p.id} className="bg-white/5 border border-white/10 p-3 mb-3 rounded-lg border-l-4 border-l-purple-500">
                <p className="font-semibold">{p.title}</p>
                {p.description && <p className="text-xs opacity-70 mb-1">{p.description}</p>}
                <p className="text-sm text-purple-400">₹{p.price}</p>
                <p className="text-xs opacity-50 mt-1">
                  {new Date(p.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </section>
        </div>
      </div>
    </RequireRole>
  );
}
