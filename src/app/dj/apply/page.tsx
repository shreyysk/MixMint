"use client";

import { useAuth } from "@/app/lib/AuthContext";
import { supabase } from "@/app/lib/supabaseClient";
import { useState } from "react";

export default function ApplyDJPage() {
  const { user } = useAuth();

  const [djName, setDjName] = useState("");
  const [bio, setBio] = useState("");
  const [genres, setGenres] = useState("");

  if (!user) {
    return <p className="p-6">You must be logged in.</p>;
  }

  const handleApply = async () => {
    const { error } = await supabase.from("dj_profiles").insert({
      user_id: user.id,
      dj_name: djName,
      slug: djName.toLowerCase().replace(/\s+/g, "-"),
      bio,
      genres: genres.split(",").map((g) => g.trim()),
    });

    if (error) {
      alert(error.message);
    } else {
      alert("DJ application submitted. Await admin approval.");
    }
  };

  return (
    <div className="p-6 text-white max-w-xl">
      <h1 className="text-2xl font-bold mb-4">Apply as DJ</h1>

      <input
        className="w-full p-2 mb-3 text-black"
        placeholder="DJ Name"
        value={djName}
        onChange={(e) => setDjName(e.target.value)}
      />

      <textarea
        className="w-full p-2 mb-3 text-black"
        placeholder="Bio"
        value={bio}
        onChange={(e) => setBio(e.target.value)}
      />

      <input
        className="w-full p-2 mb-3 text-black"
        placeholder="Genres (comma separated)"
        value={genres}
        onChange={(e) => setGenres(e.target.value)}
      />

      <button
        className="bg-purple-600 px-4 py-2"
        onClick={handleApply}
      >
        Submit Application
      </button>
    </div>
  );
}
