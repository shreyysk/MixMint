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

    // 1. Upload File
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

    if (!res.ok) {
      alert("Upload failed: " + JSON.stringify(data));
      return;
    }

    // 2. Save Track Metadata (Chained Request)
    try {
      const trackRes = await fetch("/api/tracks", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: file.name,
          price: 99,
          youtube_url: "",
          file_key: data.fileKey,
        }),
      });

      if (trackRes.ok) {
        alert("Success! File uploaded and track created.");
      } else {
        const errorData = await trackRes.json();
        alert("File uploaded, but track creation failed: " + JSON.stringify(errorData));
      }
    } catch (err: any) {
      alert("Error creating track: " + err.message);
    }
  };

  return (
    <div className="p-6 text-white">
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button className="ml-4 bg-purple-600 px-3 py-1" onClick={upload}>
        Upload & Create Track
      </button>
    </div>
  );
}