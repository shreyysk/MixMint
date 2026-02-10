"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { supabase } from "@/lib/supabaseClient";
import { TrackCard } from "@/components/ui/TrackCard";
import { AlbumCard } from "@/components/ui/AlbumCard";
import SubscriptionPlans from "@/components/features/dj/SubscriptionPlans";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";
import { Loader2, BadgeCheck, Music2, Disc3, Users, Headphones, UserPlus, UserMinus } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface DJProfileClientProps {
    initialDj: any;
    slug: string;
}

export default function DJProfileClient({ initialDj, slug }: DJProfileClientProps) {
    const { user } = useAuth();
    const [dj, setDj] = useState<any>(initialDj);
    const [tracks, setTracks] = useState<any[]>([]);
    const [albums, setAlbums] = useState<any[]>([]);
    const [purchases, setPurchases] = useState<Set<string>>(new Set());
    const [hasSub, setHasSub] = useState(false);
    const [subTier, setSubTier] = useState<string | null>(null);
    const [isFollowing, setIsFollowing] = useState(false);
    const [followerCount, setFollowerCount] = useState(0);
    const [trackPreviews, setTrackPreviews] = useState<Record<string, any[]>>({});
    const [loading, setLoading] = useState(true);
    const [followLoading, setFollowLoading] = useState(false);

    useEffect(() => {
        async function fetchData() {
            // Since we have initialDj, we can start with that, but we might want to refresh tracks/albums
            setLoading(true);
            try {
                // 1. Refresh DJ Profile (optional, but good for hits/stats)
                const { data: djData } = await supabase
                    .from("dj_profiles")
                    .select("*, profiles!inner(full_name, avatar_url)")
                    .eq("slug", slug)
                    .single();

                if (djData) setDj(djData);
                const activeDj = djData || initialDj;

                // 2. Fetch Content
                const [tracksRes, albumsRes] = await Promise.all([
                    supabase.from("tracks").select("*").eq("dj_id", activeDj.id).order("created_at", { ascending: false }),
                    supabase.from("album_packs").select("*").eq("dj_id", activeDj.id).order("created_at", { ascending: false })
                ]);

                setTracks(tracksRes.data || []);
                setAlbums(albumsRes.data || []);

                // 2.5 Fetch Previews
                if (tracksRes.data && tracksRes.data.length > 0) {
                    const trackIds = tracksRes.data.map((t: any) => t.id);
                    const { data: previewData } = await supabase
                        .from("track_previews")
                        .select("*")
                        .in("track_id", trackIds);

                    const previewMap: Record<string, any[]> = {};
                    previewData?.forEach(p => {
                        if (!previewMap[p.track_id]) previewMap[p.track_id] = [];
                        previewMap[p.track_id].push({
                            type: p.preview_type,
                            embedId: p.embed_id,
                            isPrimary: p.is_primary
                        });
                    });
                    setTrackPreviews(previewMap);
                }

                // 2.6 Fetch Follower Count
                const { count } = await supabase
                    .from("follows")
                    .select("*", { count: 'exact', head: true })
                    .eq("followed_id", activeDj.id);
                setFollowerCount(count || 0);

                // 3. User Specific
                if (user) {
                    const { data: userPurchases } = await supabase
                        .from("purchases")
                        .select("content_id")
                        .eq("user_id", user.id);

                    setPurchases(new Set(userPurchases?.map(p => p.content_id) || []));

                    const { data: userSub } = await supabase
                        .from("dj_subscriptions")
                        .select("id, tier")
                        .eq("user_id", user.id)
                        .eq("dj_id", activeDj.id)
                        .gt("expires_at", new Date().toISOString())
                        .maybeSingle();

                    setHasSub(!!userSub);
                    if (userSub) setSubTier(userSub.tier);

                    const { data: followData } = await supabase
                        .from("follows")
                        .select("*")
                        .eq("follower_id", user.id)
                        .eq("followed_id", activeDj.id)
                        .maybeSingle();
                    setIsFollowing(!!followData);
                }

            } catch (err) {
                console.error("Failed to fetch DJ info:", err);
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, [slug, user, initialDj]);

    const handleFollow = async () => {
        if (!user) {
            alert("Please login to follow DJs");
            return;
        }
        setFollowLoading(true);
        try {
            const res = await fetch("/api/dj/follow", {
                method: "POST",
                body: JSON.stringify({ djId: dj.id }),
                headers: { "Content-Type": "application/json" }
            });
            const data = await res.json();
            if (data.success) {
                setIsFollowing(data.isFollowing);
                setFollowerCount(prev => data.isFollowing ? prev + 1 : prev - 1);
            }
        } catch (err) {
            console.error("Follow error:", err);
        } finally {
            setFollowLoading(false);
        }
    };

    if (loading && !dj) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-purple-primary animate-spin" />
            </div>
        );
    }

    return (
        <main className="min-h-screen text-white pb-20">
            {/* Hero Section */}
            <div className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-purple-primary/20 via-purple-primary/5 to-transparent pointer-events-none" />
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-purple-primary/30 rounded-full blur-[150px] pointer-events-none" />

                <div className="relative pt-12 pb-16 px-6 sm:px-12">
                    <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center md:items-end gap-8">
                        <div className="relative">
                            <div className="absolute inset-0 bg-purple-primary/40 blur-xl rounded-full" />
                            <div className="relative w-44 h-44 rounded-full border-4 border-purple-primary/30 overflow-hidden bg-surface-dark shadow-purple-glow-lg">
                                {dj.profiles.avatar_url ? (
                                    <Image src={dj.profiles.avatar_url} alt={dj.dj_name} fill className="object-cover" />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center bg-gradient-purple text-white/50 text-4xl font-bold">
                                        {dj.dj_name[0]}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="text-center md:text-left flex-1">
                            <div className="flex items-center justify-center md:justify-start gap-3 mb-3">
                                <h1 className="text-4xl md:text-5xl font-heading font-bold text-white">
                                    {dj.dj_name}
                                </h1>
                                {dj.status === 'approved' && (
                                    <div className="bg-purple-primary/90 p-1.5 rounded-full shadow-purple-glow">
                                        <BadgeCheck size={18} className="text-white" />
                                    </div>
                                )}
                            </div>

                            {dj.genres?.length > 0 && (
                                <div className="flex flex-wrap justify-center md:justify-start gap-2 mb-4">
                                    {dj.genres.map((g: string) => (
                                        <span key={g} className="px-3 py-1 rounded-full text-xs font-medium bg-white/5 text-zinc-400 border border-white/5">
                                            {g}
                                        </span>
                                    ))}
                                </div>
                            )}

                            <p className="text-zinc-400 max-w-2xl mb-4">{dj.bio}</p>

                            <div className="flex items-center justify-center md:justify-start gap-6 text-sm text-zinc-500">
                                <span className="flex items-center gap-2">
                                    <Headphones size={16} className="text-purple-primary" />
                                    {tracks.length} tracks
                                </span>
                                <span className="flex items-center gap-2">
                                    <Disc3 size={16} className="text-mint-accent" />
                                    {albums.length} albums
                                </span>
                                <span className="flex items-center gap-2">
                                    <Users size={16} className="text-zinc-500" />
                                    {followerCount} followers
                                </span>
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <Button
                                onClick={handleFollow}
                                disabled={followLoading}
                                className={cn(
                                    "h-12 px-8 rounded-xl font-bold transition-all",
                                    isFollowing
                                        ? "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white"
                                        : "bg-purple-primary text-white shadow-purple-glow hover:scale-105"
                                )}
                            >
                                {followLoading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : isFollowing ? (
                                    <span className="flex items-center gap-2">
                                        <UserMinus size={18} /> Unfollow
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <UserPlus size={18} /> Follow
                                    </span>
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6 sm:px-12">
                <section className="mb-20">
                    <div className="flex items-center gap-4 mb-8">
                        <h2 className="font-heading text-2xl font-bold text-white">Choose a Plan</h2>
                        <div className="h-px flex-1 bg-white/5" />
                    </div>
                    <SubscriptionPlans djId={dj.id} djName={dj.dj_name} />
                </section>

                {tracks.length > 0 && (
                    <section className="mb-20">
                        <div className="flex items-center gap-4 mb-8">
                            <Music2 size={24} className="text-purple-primary" />
                            <h2 className="font-heading text-2xl font-bold text-white">Tracks</h2>
                            <div className="h-px flex-1 bg-white/5" />
                            <span className="text-sm text-zinc-500">{tracks.length} available</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                            {tracks.map(track => (
                                <TrackCard
                                    key={track.id}
                                    id={track.id}
                                    title={track.title}
                                    djName={dj.dj_name}
                                    djSlug={dj.slug}
                                    price={track.price}
                                    bpm={track.bpm}
                                    genre={track.genre}
                                    coverUrl={track.cover_url}
                                    isPurchased={hasSub || purchases.has(track.id)}
                                    isFanOnly={track.is_fan_only}
                                    userTier={subTier || undefined}
                                    previews={trackPreviews[track.id] || []}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {albums.length > 0 && (
                    <section>
                        <div className="flex items-center gap-4 mb-8">
                            <Disc3 size={24} className="text-mint-accent" />
                            <h2 className="font-heading text-2xl font-bold text-white">Album Packs</h2>
                            <div className="h-px flex-1 bg-white/5" />
                            <span className="text-sm text-zinc-500">{albums.length} available</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                            {albums.map(album => (
                                <AlbumCard
                                    key={album.id}
                                    id={album.id}
                                    title={album.title}
                                    djName={dj.dj_name}
                                    djSlug={dj.slug}
                                    price={album.price}
                                    trackCount={album.track_count}
                                    coverUrl={album.cover_url}
                                    isPurchased={hasSub || purchases.has(album.id)}
                                />
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </main>
    );
}
