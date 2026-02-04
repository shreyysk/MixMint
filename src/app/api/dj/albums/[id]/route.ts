import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { ok, fail } from "@/app/lib/apiResponse";

/**
 * PATCH /api/dj/albums/[id]
 * Update album metadata
 */
export async function PATCH(
    req: Request,
    { params }: { params: { id: string } }
) {
    try {
        const user = await requireAuth();
        const { id } = params;
        const body = await req.json();
        const { title, description, price } = body;

        const { data, error } = await supabaseServer
            .from('album_packs')
            .update({ title, description, price })
            .eq('id', id)
            .eq('dj_id', user.id) // album_packs.dj_id refers to profiles.id
            .select()
            .single();

        if (error) throw error;
        if (!data) return fail("Album not found or access denied", 404);

        return ok({ success: true, album: data });
    } catch (err: any) {
        console.error("[ALBUM_UPDATE_ERROR]:", err);
        return fail(err.message || "Internal server error", 500);
    }
}

/**
 * DELETE /api/dj/albums/[id]
 * Delete an album
 */
export async function DELETE(
    req: Request,
    { params }: { params: { id: string } }
) {
    try {
        const user = await requireAuth();
        const { id } = params;

        const { error } = await supabaseServer
            .from('album_packs')
            .delete()
            .eq('id', id)
            .eq('dj_id', user.id);

        if (error) throw error;

        return ok({ success: true, message: "Album deleted successfully" });
    } catch (err: any) {
        console.error("[ALBUM_DELETE_ERROR]:", err);
        return fail(err.message || "Internal server error", 500);
    }
}
