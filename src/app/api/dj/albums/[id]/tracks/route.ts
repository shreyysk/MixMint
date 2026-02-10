import { supabaseServer } from "@/lib/supabaseServer";
import { r2 } from "@/lib/r2";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { getDJStoragePath } from "@/lib/djStorage";
import { requireAuth } from "@/lib/requireAuth";
import { requireDJ } from "@/lib/requireDJ";
import { ok, fail } from "@/lib/apiResponse";
import { AlbumProcessorService } from "@/server/services/AlbumProcessorService";
import { validateMagicBytes } from "@/lib/validation";
import { logger } from "@/lib/logger";


/**
 * POST /api/dj/albums/[id]/tracks
 * Upload an individual track for a system-generated album pack.
 */
export async function POST(req: Request, { params }: { params: { id: string } }) {
  try {
    const albumId = params.id;
    const user = await requireAuth();
    await requireDJ(user.id);

    // 1. Verify Album Ownership & Status
    const { data: album, error: albumError } = await supabaseServer
      .from("album_packs")
      .select("id, dj_id, title, upload_method, processing_status")
      .eq("id", albumId)
      .single();

    if (albumError || !album) return fail("Album not found", 404);
    if (album.dj_id !== user.id) return fail("Forbidden", 403);
    
    if (album.upload_method !== 'system_generated') {
        return fail("This album does not support individual track uploads", 400);
    }

    const { data: djProfiles } = await supabaseServer
      .from("profiles")
      .select("full_name")
      .eq("id", user.id)
      .single();

    if (!djProfiles?.full_name) return fail("Profile incomplete", 400);

    // 2. Handle File Upload
    const formData = await req.formData();
    const file = formData.get("file") as File;
    const title = formData.get("title") as string;
    const order = Number(formData.get("order")) || 0;

    if (!file || !title) return fail("Missing track file or title", 400);

    const buffer = Buffer.from(await file.arrayBuffer());
    const fileExt = file.name.split(".").pop()?.toLowerCase() || "";

    if (!validateMagicBytes(buffer, fileExt)) {
      logger.warn("UPLOAD", "Magic byte mismatch", { fileName: file.name });
      return fail("File integrity check failed. Content does not match extension.", 400);
    }

    const fileKey = getDJStoragePath(
      djProfiles.full_name,
      user.id,
      "temp/tracks",
      `album_${albumId}_${Date.now()}_${file.name}`
    );

    await r2.send(new PutObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: fileKey,
      Body: buffer,
      ContentType: file.type || "audio/mpeg",
      Metadata: {
        "x-dj-id": user.id,
        "x-album-id": albumId
      }
    }));

    // 3. Register Track in DB
    const { data: track, error: trackError } = await supabaseServer
      .from("album_tracks")
      .insert({
        album_id: albumId,
        title,
        track_order: order,
        original_file_key: fileKey,
        file_size: file.size,
        format: file.type.split('/')[1] || 'mp3'
      })
      .select()
      .single();

    if (trackError) throw trackError;

    return ok({ success: true, trackId: track.id });

  } catch (err: unknown) {
    console.error("[ALBUM_TRACK_UPLOAD_ERROR]", err);
    const msg = err instanceof Error ? err.message : "Internal server error";
    return fail(msg, 500);
  }
}

/**
 * PATCH /api/dj/albums/[id]/tracks
 * Finalize the album: Trigger system-generated ZIP creation.
 */
export async function PATCH(req: Request, { params }: { params: { id: string } }) {
    try {
        const albumId = params.id;
        const user = await requireAuth();
        await requireDJ(user.id);

        const { data: album, error: albumError } = await supabaseServer
            .from("album_packs")
            .select("*, profiles!inner(full_name)")
            .eq("id", albumId)
            .single();

        if (albumError || !album) return fail("Album not found", 404);
        // Note: The join might need adjustment depending on your exact relation in Supabase
        
        // Simple manual fetch if join is complex
        const { data: coreProfile } = await supabaseServer
            .from("profiles")
            .select("full_name")
            .eq("id", user.id)
            .single();

        if (album.dj_id !== user.id) return fail("Forbidden", 403);

        // Update status to processing
        await supabaseServer
            .from("album_packs")
            .update({ processing_status: 'processing', processing_started_at: new Date().toISOString() })
            .eq("id", albumId);

        // Trigger Generation
        AlbumProcessorService.processGeneratedZip(
            albumId,
            user.id,
            coreProfile?.full_name || "DJ",
            album.title
        ).catch(err => {
            console.error(`[GEN_FAIL] Album ${albumId}:`, err);
        });

        return ok({ message: "Album finalization started. Generating ZIP..." });

    } catch (err: unknown) {
        console.error("[ALBUM_FINALIZE_ERROR]", err);
        const msg = err instanceof Error ? err.message : "Internal server error";
        return fail(msg, 500);
    }
}
