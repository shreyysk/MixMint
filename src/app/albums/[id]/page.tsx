"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useParams } from "next/navigation";

interface Album {
    id: string;
    title: string;
    description: string | null;
    price: number;
    dj_id: string;
    file_size: number;
    created_at: string;
}

export default function AlbumDetailPage() {
    const params = useParams();
    const albumId = params?.id as string;
    const { user } = useAuth();
    const [album, setAlbum] = useState<Album | null>(null);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        const fetchAlbum = async () => {
            const { data, error } = await supabase
                .from("album_packs")
                .select("*")
                .eq("id", albumId)
                .single();

            if (!error && data) {
                setAlbum(data);
            }
            setLoading(false);
        };

        if (albumId) {
            fetchAlbum();
        }
    }, [albumId]);

    async function downloadZip(albumId: string) {
        if (!user) {
            alert("Please log in to download");
            return;
        }

        setDownloading(true);

        try {
            // 1️⃣ Ask for token
            const { data: { session } } = await supabase.auth.getSession();

            const tokenRes = await fetch("/api/download-token", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({
                    content_type: "zip",
                    content_id: albumId,
                }),
            });

            if (!tokenRes.ok) {
                const err = await tokenRes.json();
                alert(err.error || "Not allowed");
                setDownloading(false);
                return;
            }

            const { token } = await tokenRes.json();

            // 2️⃣ Trigger download
            window.location.href = `/api/download?token=${token}`;

            // Reset downloading state after a delay (download started)
            setTimeout(() => setDownloading(false), 2000);
        } catch (error: any) {
            alert(error.message || "Download failed");
            setDownloading(false);
        }
    }

    if (loading) {
        return (
            <div style={{ padding: 40, textAlign: "center" }}>
                <p>Loading...</p>
            </div>
        );
    }

    if (!album) {
        return (
            <div style={{ padding: 40, textAlign: "center" }}>
                <p>Album not found</p>
            </div>
        );
    }

    return (
        <div style={{ padding: 40, maxWidth: 600, margin: "0 auto" }}>
            <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 16 }}>
                {album.title}
            </h1>

            {album.description && (
                <p style={{ marginBottom: 24, color: "#666" }}>
                    {album.description}
                </p>
            )}

            <div style={{ marginBottom: 24 }}>
                <p style={{ fontSize: 24, fontWeight: "bold" }}>
                    ${album.price}
                </p>
                <p style={{ fontSize: 14, color: "#999" }}>
                    File size: {(album.file_size / 1024 / 1024).toFixed(2)} MB
                </p>
            </div>

            <button
                onClick={() => downloadZip(album.id)}
                disabled={downloading}
                style={{
                    padding: "10px 16px",
                    background: downloading ? "#666" : "black",
                    color: "white",
                    borderRadius: 6,
                    border: "none",
                    cursor: downloading ? "not-allowed" : "pointer",
                    fontSize: 16,
                }}
            >
                {downloading ? "Starting download..." : "Download ZIP"}
            </button>

            {!user && (
                <p style={{ marginTop: 16, color: "#999", fontSize: 14 }}>
                    You must be logged in to download
                </p>
            )}
        </div>
    );
}
