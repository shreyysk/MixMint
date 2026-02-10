import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { NextRequest } from "next/server";

/**
 * GET /api/dj/albums/[id]
 * Fetch album details including processing status.
 */
export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const user = await requireAuth();
        const { id } = await params;

        const { data, error } = await supabaseServer
            .from('album_packs')
            .select('*')
            .eq('id', id)
            .eq('dj_id', user.id)
            .single();

        if (error) throw error;
        if (!data) return fail("Album not found or access denied", 404);

        return ok({ success: true, album: data });
    } catch (err: unknown) {
        console.error("[ALBUM_GET_ERROR]:", err);
        const msg = err instanceof Error ? err.message : "Internal server error";
        return fail(msg, 500);
    }
}

/**
 * PATCH /api/dj/albums/[id]
 * Update album metadata
 */
export async function PATCH(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const user = await requireAuth();
        const { id } = await params;
        const body = await req.json();
        const { title, description, price } = body;

        const { data, error } = await supabaseServer
            .from('album_packs')
            .update({ title, description, price })
            .eq('id', id)
            .eq('dj_id', user.id)
            .select()
            .single();

        if (error) throw error;
        if (!data) return fail("Album not found or access denied", 404);

        return ok({ success: true, album: data });
    } catch (err: unknown) {
        console.error("[ALBUM_UPDATE_ERROR]:", err);
        const msg = err instanceof Error ? err.message : "Internal server error";
        return fail(msg, 500);
    }
}

/**
 * DELETE /api/dj/albums/[id]
 * Delete an album
 */
export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const user = await requireAuth();
        const { id } = await params;

        // 1. Get album to find file_key
        const { data: album } = await supabaseServer
            .from('album_packs')
            .select('file_key')
            .eq('id', id)
            .eq('dj_id', user.id)
            .single();

        if (!album) return fail("Album not found or access denied", 404);

        // 2. Delete the record
        const { error } = await supabaseServer
            .from('album_packs')
            .delete()
            .eq('id', id)
            .eq('dj_id', user.id);

        if (error) throw error;

        // 3. Delete from R2
        try {
            const { DeleteObjectCommand } = await import("@aws-sdk/client-s3");
            const { r2 } = await import("@/lib/r2");
            
            await r2.send(new DeleteObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: album.file_key,
            }));
        } catch (r2Err) {
            console.error("[R2_DELETE_ERROR (ALBUM)]:", r2Err);
        }

        return ok({ success: true, message: "Album deleted successfully" });
    } catch (err: unknown) {
        console.error("[ALBUM_DELETE_ERROR]:", err);
        const msg = err instanceof Error ? err.message : "Internal server error";
        return fail(msg, 500);
    }
}
