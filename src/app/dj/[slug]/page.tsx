import { supabaseServer } from "@/lib/supabaseServer";
import { Metadata } from "next";
import DJProfileClient from "./ProfileClient";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata(
  { params }: Props
): Promise<Metadata> {
  const { slug } = await params;
  const { data: dj } = await supabaseServer
    .from("dj_profiles")
    .select("dj_name, bio, genres")
    .eq("slug", slug)
    .maybeSingle();

  if (!dj) return { title: "DJ Not Found | MixMint" };

  return {
    title: `${dj.dj_name} | MixMint Storefront`,
    description: dj.bio || `Check out ${dj.dj_name}'s exclusive tracks and albums on MixMint.`,
    keywords: [...(dj.genres || []), "MixMint", "DJ", "Music Marketplace"],
    openGraph: {
      title: `${dj.dj_name} on MixMint`,
      description: dj.bio || `Stream and download professional DJ content from ${dj.dj_name}.`,
      type: "website",
    }
  };
}

export default async function DJProfilePage({ params }: Props) {
  const { slug } = await params;

  // Preliminary fetch for the server component to avoid flicker
  const { data: dj } = await supabaseServer
    .from("dj_profiles")
    .select("*, profiles!inner(full_name, avatar_url)")
    .eq("slug", slug)
    .single();

  if (!dj) notFound();

  return <DJProfileClient initialDj={dj} slug={slug} />;
}
