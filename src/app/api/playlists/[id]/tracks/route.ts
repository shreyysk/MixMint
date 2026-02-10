import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/playlists/[id]/tracks
 * Get tracks in a playlist
 */
export async function GET(req: Request, { params }: { params: { id: string } }) {
  try {
    const user = await requireAuth();
    const playlistId = params.id;

    // Verify ownership
    const { data: playlist } = await supabaseServer
      .from("playlists")
      .select("user_id, is_public")
      .eq("id", playlistId)
      .single();

    if (!playlist) {
      return fail("Playlist not found", 404);
    }

    if (playlist.user_id !== user.id && !playlist.is_public) {
      return fail("Forbidden", 403);
    }

    const { data: tracks, error } = await supabaseServer
      .from("playlist_tracks")
      .select(`
        *,
        tracks (
          id,
          title,
          price,
          genre,
          bpm,
          cover_url,
          dj_profiles (dj_name)
        )
      `)
      .eq("playlist_id", playlistId)
      .order("position", { ascending: true });

    if (error) throw error;

    return ok({ tracks });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * POST /api/playlists/[id]/tracks
 * Add track to playlist
 */
export async function POST(req: Request, { params }: { params: { id: string } }) {
  try {
    const user = await requireAuth();
    const playlistId = params.id;
    const { trackId } = await req.json();

    if (!trackId) {
      return fail("Track ID required", 400);
    }

    // Verify ownership
    const { data: playlist } = await supabaseServer
      .from("playlists")
      .select("user_id")
      .eq("id", playlistId)
      .single();

    if (!playlist || playlist.user_id !== user.id) {
      return fail("Forbidden", 403);
    }

    // Get next position
    const { count } = await supabaseServer
      .from("playlist_tracks")
      .select("*", { count: "exact", head: true })
      .eq("playlist_id", playlistId);

    const position = (count || 0) + 1;

    const { error } = await supabaseServer
      .from("playlist_tracks")
      .insert({
        playlist_id: playlistId,
        track_id: trackId,
        position
      });

    if (error) throw error;

    // Update playlist updated_at
    await supabaseServer
      .from("playlists")
      .update({ updated_at: new Date().toISOString() })
      .eq("id", playlistId);

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * DELETE /api/playlists/[id]/tracks
 * Remove track from playlist
 */
export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  try {
    const user = await requireAuth();
    const playlistId = params.id;
    const { searchParams } = new URL(req.url);
    const trackId = searchParams.get("trackId");

    if (!trackId) {
      return fail("Track ID required", 400);
    }

    // Verify ownership
    const { data: playlist } = await supabaseServer
      .from("playlists")
      .select("user_id")
      .eq("id", playlistId)
      .single();

    if (!playlist || playlist.user_id !== user.id) {
      return fail("Forbidden", 403);
    }

    const { error } = await supabaseServer
      .from("playlist_tracks")
      .delete()
      .eq("playlist_id", playlistId)
      .eq("track_id", trackId);

    if (error) throw error;

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
