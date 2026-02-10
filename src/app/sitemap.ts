import { supabaseServer } from "@/lib/supabaseServer";
import { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = "https://mixmint.site";

  // 1. Fetch all DJ slugs
  const { data: djs } = await supabaseServer
    .from("dj_profiles")
    .select("slug, updated_at")
    .eq("status", "approved");

  // 2. Fetch all Track IDs
  const { data: tracks } = await supabaseServer
    .from("tracks")
    .select("id, updated_at")
    .eq("status", "active");

  const djUrls = (djs || []).map((dj) => ({
    url: `${baseUrl}/dj/${dj.slug}`,
    lastModified: dj.updated_at,
    changeFrequency: "weekly" as const,
    priority: 0.8,
  }));

  const trackUrls = (tracks || []).map((track) => ({
    url: `${baseUrl}/track/${track.id}`,
    lastModified: track.updated_at,
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${baseUrl}/explore`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.9,
    },
    ...djUrls,
    ...trackUrls,
  ];
}
