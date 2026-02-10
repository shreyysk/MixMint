import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/dj/milestones
 * Returns DJ's achieved milestones
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();

    // Verify DJ status
    const { data: djProfile } = await supabaseServer
      .from("dj_profiles")
      .select("id")
      .eq("id", user.id)
      .single();

    if (!djProfile) {
      return fail("Not a DJ", 403);
    }

    const { data: milestones, error } = await supabaseServer
      .from("dj_milestones")
      .select("*")
      .eq("dj_id", user.id)
      .order("achieved_at", { ascending: false });

    if (error) throw error;

    return ok({ milestones });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
