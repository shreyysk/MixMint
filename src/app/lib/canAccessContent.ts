import { supabaseServer } from "@/app/lib/supabaseServer";

export async function canAccessContent(
  userId: string,
  contentType: "track" | "zip",
  contentId: string
): Promise<{ allowed: boolean; via: "purchase" | "subscription" | null }> {

  // 1️⃣ Purchase always wins
  const { data: purchase } = await supabaseServer
    .from("purchases")
    .select("id")
    .eq("user_id", userId)
    .eq("content_type", contentType)
    .eq("content_id", contentId)
    .single();

  if (purchase) {
    return { allowed: true, via: "purchase" };
  }

  // 2️⃣ Fetch content owner
  const table = contentType === "track" ? "tracks" : "album_packs";

  const { data: content } = await supabaseServer
    .from(table)
    .select("dj_id")
    .eq("id", contentId)
    .single();

  if (!content) {
    return { allowed: false, via: null };
  }

  // 3️⃣ Check subscription
  const { data: sub } = await supabaseServer
    .from("dj_subscriptions")
    .select("*")
    .eq("user_id", userId)
    .eq("dj_id", content.dj_id)
    .gt("expires_at", new Date().toISOString())
    .single();

  if (!sub) {
    return { allowed: false, via: null };
  }

  if (contentType === "track" && sub.tracks_used < sub.track_quota) {
    return { allowed: true, via: "subscription" };
  }

  if (contentType === "zip" && sub.zips_used < sub.zip_quota) {
    return { allowed: true, via: "subscription" };
  }

  return { allowed: false, via: null };
}
