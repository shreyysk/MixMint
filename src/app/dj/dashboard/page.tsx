"use client";

import { useAuth } from "@/app/lib/AuthContext";
import { supabase } from "@/app/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/app/components/RequireRole";

export default function DJDashboard() {
  const { user } = useAuth();
  const [tracks, setTracks] = useState<any[]>([]);

    useEffect(() => {
    const loadTracks = async () => {
        const {
        data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) {
        console.warn("No session token, skipping track fetch");
        return;
        }

        const res = await fetch("/api/dj/tracks", {
        headers: {
            Authorization: `Bearer ${session.access_token}`,
        },
        });

        const json = await res.json();
        console.log("DJ tracks response:", json);

        setTracks(json.tracks || []);
    };

    if (user) {
        loadTracks();
    }
    }, [user]);


  return (
    <RequireRole allowed={["dj", "admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">Your Tracks</h1>

        {tracks.length === 0 && <p>No tracks uploaded yet.</p>}

        {tracks.map((t) => (
          <div key={t.id} className="border p-3 mb-3">
            <p className="font-semibold">{t.title}</p>
            <p>Price: ₹{t.price}</p>
            <p className="text-sm opacity-70">
              Uploaded: {new Date(t.created_at).toLocaleDateString()}
            </p>
          </div>
        ))}
      </div>
    </RequireRole>
  );
}
