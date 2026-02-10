import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/feed
 * Returns personalized activity feed for the authenticated user
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();
    const { searchParams } = new URL(req.url);
    const limit = Number(searchParams.get("limit")) || 20;
    const unreadOnly = searchParams.get("unread") === "true";

    let query = supabaseServer
      .from("activity_feed")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(limit);

    if (unreadOnly) {
      query = query.eq("is_read", false);
    }

    const { data: feed, error } = await query;

    if (error) throw error;

    return ok({ feed });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * PATCH /api/feed
 * Mark feed items as read
 */
export async function PATCH(req: Request) {
  try {
    const user = await requireAuth();
    const { feedIds } = await req.json();

    if (!feedIds || !Array.isArray(feedIds)) {
      return fail("Feed IDs array required", 400);
    }

    const { error } = await supabaseServer
      .from("activity_feed")
      .update({ is_read: true })
      .in("id", feedIds)
      .eq("user_id", user.id);

    if (error) throw error;

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
