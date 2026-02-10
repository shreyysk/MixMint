import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { trackInteraction } from "@/lib/recommendations";

/**
 * POST /api/interactions/track
 * Log user interaction for recommendations engine
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const { trackId, djId, interactionType } = await req.json();

    if (!interactionType || !['view', 'purchase', 'wishlist', 'follow_dj', 'play'].includes(interactionType)) {
      return fail("Invalid interaction type", 400);
    }

    await trackInteraction(user.id, trackId || null, djId || null, interactionType);

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
