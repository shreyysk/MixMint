"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import Link from "next/link";

interface Album {
    id: string;
    title: string;
    price: number;
    file_size: number;
    created_at: string;
}

export default function AlbumsPage() {
    const [albums, setAlbums] = useState<Album[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAlbums = async () => {
            const { data, error } = await supabase
                .from("album_packs")
                .select("id, title, price, file_size, created_at")
                .order("created_at", { ascending: false });

            if (!error && data) {
                setAlbums(data);
            }
            setLoading(false);
        };

        fetchAlbums();
    }, []);

    if (loading) {
        return (
            <div style={{ padding: 40, textAlign: "center" }}>
                <p>Loading albums...</p>
            </div>
        );
    }

    return (
        <div style={{ padding: 40, maxWidth: 800, margin: "0 auto" }}>
            <h1 style={{ fontSize: 32, fontWeight: "bold", marginBottom: 24 }}>
                Available Album Packs
            </h1>

            {albums.length === 0 ? (
                <p style={{ color: "#666" }}>No albums available yet.</p>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {albums.map((album) => (
                        <Link
                            key={album.id}
                            href={`/albums/${album.id}`}
                            style={{
                                padding: 20,
                                border: "1px solid #ddd",
                                borderRadius: 8,
                                textDecoration: "none",
                                color: "inherit",
                                display: "block",
                                transition: "background 0.2s",
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "#f5f5f5")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
                        >
                            <h2 style={{ fontSize: 20, fontWeight: "bold", marginBottom: 8 }}>
                                {album.title}
                            </h2>
                            <div style={{ display: "flex", gap: 16, fontSize: 14, color: "#666" }}>
                                <span>${album.price}</span>
                                <span>•</span>
                                <span>{(album.file_size / 1024 / 1024).toFixed(2)} MB</span>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
