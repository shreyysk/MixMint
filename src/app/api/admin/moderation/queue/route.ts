import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/admin/moderation/queue
 * Returns content moderation queue for admin review
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();

    // Check admin role
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    const { searchParams } = new URL(req.url);
    const status = searchParams.get("status") || "pending";

    const { data: queue, error } = await supabaseServer
      .from("moderation_queue")
      .select(`
        *,
        tracks (
          id,
          title,
          dj_profiles (dj_name)
        ),
        matched_track:matched_track_id (
          title,
          dj_profiles (dj_name)
        )
      `)
      .eq("status", status)
      .order("created_at", { ascending: false })
      .limit(50);

    if (error) throw error;

    return ok({ queue });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * PATCH /api/admin/moderation/queue
 * Update moderation queue item status
 */
export async function PATCH(req: Request) {
  try {
    const user = await requireAuth();

    // Check admin role
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    const { queueId, status, adminNotes } = await req.json();

    if (!queueId || !status) {
      return fail("Queue ID and status required", 400);
    }

    const { error } = await supabaseServer
      .from("moderation_queue")
      .update({
        status,
        reviewed_by: user.id,
        reviewed_at: new Date().toISOString(),
        admin_notes: adminNotes
      })
      .eq("id", queueId);

    if (error) throw error;

    // If rejected, disable the track
    if (status === "rejected") {
      const { data: queueItem } = await supabaseServer
        .from("moderation_queue")
        .select("track_id")
        .eq("id", queueId)
        .single();

      if (queueItem) {
        await supabaseServer
          .from("tracks")
          .update({ is_active: false })
          .eq("id", queueItem.track_id);
      }
    }

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
