import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { awardEngagementPoints } from "@/lib/rewards";


/**
 * GET /api/dj/follow?djId=...
 * Check if the current user follows a specific DJ.
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();
    const { searchParams } = new URL(req.url);
    const djId = searchParams.get("djId");

    if (!djId) return fail("DJ ID required", 400);

    const { data, error } = await supabaseServer
      .from("follows")
      .select("*")
      .eq("follower_id", user.id)
      .eq("followed_id", djId)
      .maybeSingle();

    if (error) throw error;

    return ok({ isFollowing: !!data });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal server error", 500);
  }
}

/**
 * POST /api/dj/follow
 * Toggle follow status for a DJ.
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const { djId } = await req.json();

    if (!djId) return fail("DJ ID required", 400);

    // Check existing
    const { data: existing } = await supabaseServer
      .from("follows")
      .select("*")
      .eq("follower_id", user.id)
      .eq("followed_id", djId)
      .maybeSingle();

    if (existing) {
      // Unfollow
      const { error } = await supabaseServer
        .from("follows")
        .delete()
        .eq("follower_id", user.id)
        .eq("followed_id", djId);
      
      if (error) throw error;
      return ok({ success: true, isFollowing: false });
    } else {
      // Follow
      const { error } = await supabaseServer
        .from("follows")
        .insert({
          follower_id: user.id,
          followed_id: djId
        });
      
      if (error) throw error;
      
      // Award points (non-blocking)
      awardEngagementPoints(user.id, djId, 'follow');
      
      return ok({ success: true, isFollowing: true });

    }
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal server error", 500);
  }
}
