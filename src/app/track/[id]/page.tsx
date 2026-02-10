import { supabaseServer } from "@/lib/supabaseServer";
import { Metadata } from "next";
import TrackDetailClient from "./TrackDetailClient";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata(
  { params }: Props
): Promise<Metadata> {
  const { id } = await params;
  const { data: track } = await supabaseServer
    .from("tracks")
    .select(`
        title, 
        description, 
        genre,
        dj_profiles (dj_name)
    `)
    .eq("id", id)
    .maybeSingle();

  if (!track) return { title: "Track Not Found | MixMint" };

  const djName = (track.dj_profiles as any)?.dj_name || "Unknown DJ";

  return {
    title: `${track.title} by ${djName} | MixMint`,
    description: track.description || `Download ${track.title} by ${djName} exclusively on MixMint.`,
    keywords: [track.title, djName, track.genre || "", "MixMint", "DJ Track"],
    openGraph: {
      title: `${track.title} - ${djName}`,
      description: `Premium audio release from ${djName}.`,
      type: "music.song",
    }
  };
}

export default async function TrackDetailPage({ params }: Props) {
  const { id } = await params;

  const { data: track, error } = await supabaseServer
    .from("tracks")
    .select(`
      *,
      dj_profiles:dj_id (
        dj_name,
        slug
      )
    `)
    .eq("id", id)
    .eq("status", "active")
    .single();

  if (error || !track) notFound();

  // Transform for client component
  const transformedTrack = {
    ...track,
    dj_profile: track.dj_profiles
  };

  return <TrackDetailClient initialTrack={transformedTrack as any} trackId={id} />;
}
