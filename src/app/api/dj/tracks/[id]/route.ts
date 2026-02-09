import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { NextRequest } from "next/server";

/**
 * PATCH /api/dj/tracks/[id]
 * Update track metadata
 */
export async function PATCH(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const user = await requireAuth();
        const { id } = await params;
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
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const user = await requireAuth();
        const { id } = await params;

        // Get DJ profile
        const { data: djProfile } = await supabaseServer
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (!djProfile) return fail("Not a DJ", 403);

        // 1. Get track to find file_key
        const { data: track } = await supabaseServer
            .from('tracks')
            .select('file_key')
            .eq('id', id)
            .eq('dj_id', djProfile.id)
            .single();

        if (!track) return fail("Track not found or access denied", 404);

        // 2. Delete the record
        const { error } = await supabaseServer
            .from('tracks')
            .delete()
            .eq('id', id)
            .eq('dj_id', djProfile.id);

        if (error) throw error;

        // 3. Delete from R2 (Fire and forget or best effort)
        try {
            const { DeleteObjectCommand } = await import("@aws-sdk/client-s3");
            const { r2 } = await import("@/lib/r2");
            
            await r2.send(new DeleteObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: track.file_key,
            }));
        } catch (r2Err) {
            console.error("[R2_DELETE_ERROR]:", r2Err);
            // We don't fail the request if R2 delete fails, but we log it.
        }

        return ok({ success: true, message: "Track deleted successfully" });
    } catch (err: any) {
        console.error("[TRACK_DELETE_ERROR]:", err);
        return fail(err.message || "Internal server error", 500);
    }
}
