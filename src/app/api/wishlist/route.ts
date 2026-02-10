import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/wishlist
 * Returns the current user's wishlist with content details.
 */
export async function GET() {
  try {
    const user = await requireAuth();

    const { data, error } = await supabaseServer
      .from("wishlists")
      .select("*")
      .eq("user_id", user.id);

    if (error) throw error;

    return ok({ items: data });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal server error", 500);
  }
}

/**
 * POST /api/wishlist
 * Toggles a track/album in the wishlist.
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const { contentId, contentType } = await req.json();

    if (!contentId || !contentType) return fail("Missing contentId or contentType", 400);

    const { data: existing } = await supabaseServer
      .from("wishlists")
      .select("*")
      .eq("user_id", user.id)
      .eq("content_id", contentId)
      .eq("content_type", contentType)
      .maybeSingle();

    if (existing) {
      const { error } = await supabaseServer
        .from("wishlists")
        .delete()
        .eq("user_id", user.id)
        .eq("content_id", contentId)
        .eq("content_type", contentType);
      
      if (error) throw error;
      return ok({ success: true, isWishlisted: false });
    } else {
      const { error } = await supabaseServer
        .from("wishlists")
        .insert({
          user_id: user.id,
          content_id: contentId,
          content_type: contentType
        });
      
      if (error) throw error;
      return ok({ success: true, isWishlisted: true });
    }
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal server error", 500);
  }
}
