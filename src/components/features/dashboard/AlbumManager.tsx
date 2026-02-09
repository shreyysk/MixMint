
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useAuth } from "@/lib/AuthContext";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Edit, Trash } from "lucide-react";
import { Skeleton } from "@/components/ui/Skeleton";

interface Album {
    id: string;
    title: string;
    price: number;
}

export function AlbumManager() {
    const { user } = useAuth();
    const [albums, setAlbums] = useState<Album[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchAlbums();
        }
    }, [user]);

    async function fetchAlbums() {
        setLoading(true);
        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('id', user.id)
            .single();

        if (djError || !djProfile) {
            console.error("Error fetching DJ profile for albums", djError);
            setLoading(false);
            return;
        }

        const { data, error } = await supabase
            .from("album_packs")
            .select("id, title, price")
            .eq("dj_id", djProfile.id)
            .order("created_at", { ascending: false });

        if (error) {
            console.error("Error fetching albums:", error);
        } else {
            setAlbums(data);
        }
        setLoading(false);
    }

    async function deleteAlbum(id: string) {
        if (confirm("Are you sure you want to delete this album?")) {
            const { error } = await supabase.from("album_packs").delete().eq("id", id);
            if (error) {
                alert("Error deleting album");
            } else {
                fetchAlbums();
            }
        }
    }

    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Actions</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {loading ? (
                    Array.from({ length: 2 }).map((_, i) => (
                        <TableRow key={i}>
                            <TableCell><Skeleton className="h-5 w-3/4" /></TableCell>
                            <TableCell><Skeleton className="h-5 w-1/2" /></TableCell>
                            <TableCell><Skeleton className="h-8 w-24" /></TableCell>
                        </TableRow>
                    ))
                ) : albums.map(album => (
                    <TableRow key={album.id}>
                        <TableCell>{album.title}</TableCell>
                        <TableCell>₹{album.price.toFixed(2)}</TableCell>
                        <TableCell>
                            <Button variant="ghost" size="icon">
                                <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => deleteAlbum(album.id)}>
                                <Trash className="h-4 w-4 text-red-500" />
                            </Button>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}
