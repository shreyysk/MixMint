import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { getRecommendations } from "@/lib/recommendations";

/**
 * GET /api/recommendations
 * Returns personalized track recommendations for the authenticated user
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();
    const { searchParams } = new URL(req.url);
    const limit = Number(searchParams.get("limit")) || 10;

    const recommendations = await getRecommendations(user.id, limit);

    return ok({ recommendations });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
