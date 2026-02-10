import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabaseServer";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/tracks
 * Advanced search with filters
 */
export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    
    // Search and filter parameters
    const search = searchParams.get("search") || "";
    const genres = searchParams.get("genres")?.split(",").filter(Boolean) || [];
    const minBpm = Number(searchParams.get("minBpm")) || 0;
    const maxBpm = Number(searchParams.get("maxBpm")) || 300;
    const minPrice = Number(searchParams.get("minPrice")) || 0;
    const maxPrice = Number(searchParams.get("maxPrice")) || 999999;
    const djTier = searchParams.get("djTier");
    const sortBy = searchParams.get("sortBy") || "newest"; // newest, price_low, price_high, popular
    const limit = Number(searchParams.get("limit")) || 20;

    let query = supabaseServer
      .from("tracks")
      .select(`
        *,
        dj_profiles (
          dj_name,
          referral_tier,
          slug
        )
      `)
      .eq("is_active", true);

    // Text search
    if (search) {
      query = query.or(`title.ilike.%${search}%,description.ilike.%${search}%`);
    }

    // Genre filter
    if (genres.length > 0) {
      query = query.in("genre", genres);
    }

    // BPM range
    if (minBpm > 0 || maxBpm < 300) {
      query = query.gte("bpm", minBpm).lte("bpm", maxBpm);
    }

    // Price range
    query = query.gte("price", minPrice).lte("price", maxPrice);

    // DJ Tier filter (requires join)
    if (djTier) {
      query = query.eq("dj_profiles.referral_tier", djTier);
    }

    // Sorting
    switch (sortBy) {
      case "price_low":
        query = query.order("price", { ascending: true });
        break;
      case "price_high":
        query = query.order("price", { ascending: false });
        break;
      case "popular":
        query = query.order("download_count", { ascending: false });
        break;
      case "newest":
      default:
        query = query.order("created_at", { ascending: false });
    }

    query = query.limit(limit);

    const { data: tracks, error } = await query;

    if (error) throw error;

    return ok({ tracks });
  } catch (err: any) {
    return fail(err.message || "Internal error", 500);
  }
}

export async function POST(req: Request) {
  const authHeader = req.headers.get("authorization");
  if (!authHeader) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = authHeader.replace("Bearer ", "");
  const { data: userData } = await supabaseServer.auth.getUser(token);

  if (!userData?.user) {
    return NextResponse.json({ error: "Invalid user" }, { status: 401 });
  }

  const body = await req.json();

  const { title, price, youtube_url, file_key } = body;

  const { data: dj } = await supabaseServer
    .from("dj_profiles")
    .select("id")
    .eq("user_id", userData.user.id)
    .eq("status", "approved")
    .single();

  if (!dj) {
    return NextResponse.json({ error: "Not a DJ" }, { status: 403 });
  }

  const { error } = await supabaseServer.from("tracks").insert({
    dj_id: dj.id,
    title,
    price,
    youtube_url,
    file_key,
  });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  return NextResponse.json({ success: true });
}
