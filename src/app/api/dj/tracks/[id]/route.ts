import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { ok, fail } from "@/app/lib/apiResponse";

/**
 * PATCH /api/dj/tracks/[id]
 * Update track metadata
 */
export async function PATCH(
    req: Request,
    { params }: { params: { id: string } }
) {
    try {
        const user = await requireAuth();
        const { id } = params;
        const body = await req.json();
        const { title, price, youtube_url } = body;

        // Get DJ profile
        const { data: djProfile } = await supabaseServer
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (!djProfile) return fail("Not a DJ", 403);

        const { data, error } = await supabaseServer
            .from('tracks')
            .update({ title, price, youtube_url })
            .eq('id', id)
            .eq('dj_id', djProfile.id)
            .select()
            .single();

        if (error) throw error;
        if (!data) return fail("Track not found or access denied", 404);

        return ok({ success: true, track: data });
    } catch (err: any) {
        console.error("[TRACK_UPDATE_ERROR]:", err);
        return fail(err.message || "Internal server error", 500);
    }
}

/**
 * DELETE /api/dj/tracks/[id]
 * Delete a track
 */
export async function DELETE(
    req: Request,
    { params }: { params: { id: string } }
) {
    try {
        const user = await requireAuth();
        const { id } = params;

        // Get DJ profile
        const { data: djProfile } = await supabaseServer
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (!djProfile) return fail("Not a DJ", 403);

        // TODO: We should also delete the file from R2
        // But for now, we just delete the record
        const { error } = await supabaseServer
            .from('tracks')
            .delete()
            .eq('id', id)
            .eq('dj_id', djProfile.id);

        if (error) throw error;

        return ok({ success: true, message: "Track deleted successfully" });
    } catch (err: any) {
        console.error("[TRACK_DELETE_ERROR]:", err);
        return fail(err.message || "Internal server error", 500);
    }
}
