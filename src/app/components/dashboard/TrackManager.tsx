
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/Table";
import { Button } from "@/app/components/ui/Button";
import { Edit, Trash } from "lucide-react";
import { Skeleton } from "@/app/components/ui/Skeleton";

interface Track {
    id: string;
    title: string;
    price: number;
    status: string;
}

export function TrackManager() {
    const { user } = useAuth();
    const [tracks, setTracks] = useState<Track[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchTracks();
        }
    }, [user]);

    async function fetchTracks() {
        setLoading(true);
        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();
        
        if (djError || !djProfile) {
            console.error("Error fetching DJ profile for tracks", djError);
            setLoading(false);
            return;
        }

        const { data, error } = await supabase
            .from("tracks")
            .select("id, title, price, status")
            .eq("dj_id", djProfile.id)
            .order("created_at", { ascending: false });

        if (error) {
            console.error("Error fetching tracks:", error);
        } else {
            setTracks(data);
        }
        setLoading(false);
    }

    async function deleteTrack(id: string) {
        if(confirm("Are you sure you want to delete this track?")) {
            const { error } = await supabase.from("tracks").delete().eq("id", id);
            if (error) {
                alert("Error deleting track");
            } else {
                fetchTracks();
            }
        }
    }
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {loading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                        <TableRow key={i}>
                            <TableCell><Skeleton className="h-5 w-3/4" /></TableCell>
                            <TableCell><Skeleton className="h-5 w-1/2" /></TableCell>
                            <TableCell><Skeleton className="h-5 w-1/2" /></TableCell>
                            <TableCell><Skeleton className="h-8 w-24" /></TableCell>
                        </TableRow>
                    ))
                ) : tracks.map(track => (
                    <TableRow key={track.id}>
                        <TableCell>{track.title}</TableCell>
                        <TableCell>${track.price.toFixed(2)}</TableCell>
                        <TableCell>{track.status}</TableCell>
                        <TableCell>
                            <Button variant="ghost" size="icon">
                                <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => deleteTrack(track.id)}>
                                <Trash className="h-4 w-4 text-red-500" />
                            </Button>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}
