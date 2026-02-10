import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { awardEngagementPoints } from "@/lib/rewards";

/**
 * GET /api/tracks/[id]/reviews
 * List reviews for a track.
 */
export async function GET(req: Request, { params }: { params: { id: string } }) {
  try {
    const trackId = params.id;

    const { data: reviews, error } = await supabaseServer
      .from("reviews")
      .select("*, profiles(full_name, avatar_url)")
      .eq("track_id", trackId)
      .order("created_at", { ascending: false });

    if (error) throw error;

    return ok({ reviews });
  } catch (err: any) {
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * POST /api/tracks/[id]/reviews
 * Create a review for a track.
 */
export async function POST(req: Request, { params }: { params: { id: string } }) {
  try {
    const user = await requireAuth();
    const trackId = params.id;
    const { rating, comment } = await req.json();

    if (!rating || rating < 1 || rating > 5) {
      return fail("Rating between 1 and 5 required", 400);
    }

    // 1. Check if user already reviewed
    const { data: existing } = await supabaseServer
        .from("reviews")
        .select("id")
        .eq("user_id", user.id)
        .eq("track_id", trackId)
        .maybeSingle();
    
    if (existing) {
        return fail("You have already reviewed this track", 400);
    }

    // 2. Insert Review
    const { data: review, error } = await supabaseServer
      .from("reviews")
      .insert({
        user_id: user.id,
        track_id: trackId,
        rating,
        comment
      })
      .select()
      .single();

    if (error) throw error;

    // 3. Award points (non-blocking)
    awardEngagementPoints(user.id, trackId, 'review');

    return ok({ success: true, review });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
