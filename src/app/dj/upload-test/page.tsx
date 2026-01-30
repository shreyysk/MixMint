"use client";

import { useAuth } from "@/app/lib/AuthContext";
import { useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";

export default function UploadTest() {
  const { user } = useAuth();
  const [file, setFile] = useState<File | null>(null);

  if (!user) return <p>Login required</p>;

  const upload = async () => {
    if (!file) return;

    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session) {
      alert("Not logged in");
      return;
    }

    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch("/api/upload", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      body: fd,
    });

    const data = await res.json();
    alert(JSON.stringify(data));
  };

  return (
    <div className="p-6 text-white">
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button className="ml-4 bg-purple-600 px-3 py-1" onClick={upload}>
        Upload
      </button>
    </div>
  );
}