"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import RequireRole from "@/app/components/RequireRole";

type Track = {
  id: string;
  title: string;
  price: number;
  created_at: string;
};

export default function DJTracksPage() {
  const { user, loading } = useAuth();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingTracks, setLoadingTracks] = useState(true);

  useEffect(() => {
    const loadTracks = async () => {
      setLoadingTracks(true);
      setError(null);

      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        console.warn("No valid session found");
        setError("Session not available");
        setLoadingTracks(false);
        return;
      }

      const res = await fetch("/api/dj/tracks", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      const json = await res.json();
      console.log("DJ tracks response:", json);

      if (!res.ok) {
        setError(json.error || "Failed to load tracks");
        setTracks([]);
      } else {
        setTracks(json.tracks || []);
      }

      setLoadingTracks(false);
    };

    if (user && !loading) {
      loadTracks();
    }
  }, [user, loading]);

  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">Your Tracks</h1>

        {loadingTracks && <p>Loading tracks...</p>}

        {!loadingTracks && error && (
          <p className="text-red-400">{error}</p>
        )}

        {!loadingTracks && !error && tracks.length === 0 && (
          <p>No tracks uploaded yet.</p>
        )}

        {!loadingTracks &&
          tracks.map((track) => (
            <div
              key={track.id}
              className="border border-white/20 rounded p-4 mb-3"
            >
              <p className="font-semibold">{track.title}</p>
              <p className="text-sm opacity-80">Price: ₹{track.price}</p>
              <p className="text-xs opacity-60">
                Uploaded on{" "}
                {new Date(track.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
      </div>
    </RequireRole>
  );
}
