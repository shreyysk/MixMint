import { supabaseServer } from "@/lib/supabaseServer";
import { DJService } from "@/server/services/DJService";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * POST /api/dj/apply
 * Allows a user to apply for a DJ partner profile.
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const body = await req.json();
    const { dj_name, slug } = body;

    if (!dj_name || !slug) {
      return fail("DJ Name and Slug are required", 400);
    }

    // Use DJService to handle application logic
    const result = await DJService.apply(user.id, { dj_name, slug });

    return ok(result);

  } catch (err: any) {
    console.error("[DJ_APPLY_ERROR]:", err);
    return fail(err.message || "Internal server error", 500);
  }
}
