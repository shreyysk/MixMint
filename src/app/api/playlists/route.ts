import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/playlists
 * Returns user's playlists
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();

    const { data: playlists, error } = await supabaseServer
      .from("playlists")
      .select(`
        *,
        playlist_tracks (count)
      `)
      .eq("user_id", user.id)
      .order("updated_at", { ascending: false });

    if (error) throw error;

    return ok({ playlists });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * POST /api/playlists
 * Create a new playlist
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const { name, description, isSmart, smartCriteria } = await req.json();

    if (!name) {
      return fail("Playlist name required", 400);
    }

    const { data: playlist, error } = await supabaseServer
      .from("playlists")
      .insert({
        user_id: user.id,
        name,
        description,
        is_smart: isSmart || false,
        smart_criteria: smartCriteria
      })
      .select()
      .single();

    if (error) throw error;

    return ok({ playlist });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * DELETE /api/playlists
 * Delete a playlist
 */
export async function DELETE(req: Request) {
  try {
    const user = await requireAuth();
    const { searchParams } = new URL(req.url);
    const playlistId = searchParams.get("id");

    if (!playlistId) {
      return fail("Playlist ID required", 400);
    }

    const { error } = await supabaseServer
      .from("playlists")
      .delete()
      .eq("id", playlistId)
      .eq("user_id", user.id);

    if (error) throw error;

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
