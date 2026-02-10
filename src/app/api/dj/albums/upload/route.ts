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
 * POST /api/dj/albums/upload
 * Standardized DJ album (ZIP) uploader with background processing.
 */
export async function POST(req: Request) {
  try {
    // 1. AUTH & ROLE CHECK
    const user = await requireAuth();
    await requireDJ(user.id);

    const { data: djProfile, error: profileError } = await supabaseServer
      .from("dj_profiles")
      .select("id, status")
      .eq("id", user.id)
      .single();

    if (profileError || !djProfile || djProfile.status !== "approved") {
      return fail("DJ account not approved", 403);
    }

    const { data: coreProfile } = await supabaseServer
      .from("profiles")
      .select("full_name")
      .eq("id", user.id)
      .single();

    if (!coreProfile?.full_name) {
      return fail("Profile incomplete", 400);
    }

    // 2. FORM DATA
    const formData = await req.formData();
    const file = formData.get("file") as File;
    const title = formData.get("title") as string;
    const description = formData.get("description") as string;
    const price = Number(formData.get("price"));
    const isFanOnly = formData.get("is_fan_only") === "true";
    const uploadMethod = (formData.get("upload_method") as string) || "direct_zip";

    if (!file || !title || isNaN(price)) {
      return fail("Missing required fields", 400);
    }

    if (price < 79) {
      return fail("Minimum album pack price is ₹79", 400);
    }

    // 3. STORAGE LOGIC (Temp)
    const fileName = file.name;
    const buffer = Buffer.from(await file.arrayBuffer());
    const fileExt = fileName.split(".").pop()?.toLowerCase() || "";

    if (!validateMagicBytes(buffer, fileExt)) {
      logger.warn("UPLOAD", "Magic byte mismatch", { fileName, type: file.type });
      return fail("File integrity check failed. Content does not match extension.", 400);
    }

    // Store in temp folder first for processing
    const tempKey = getDJStoragePath(
      coreProfile.full_name,
      user.id,
      "temp/albums",
      `raw_${Date.now()}_${fileName}`
    );


    await r2.send(new PutObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: tempKey,
      Body: buffer,
      ContentType: file.type || "application/zip",
      Metadata: {
        "x-dj-id": user.id,
        "x-upload-type": "raw_album_zip"
      },
    }));

    // 4. DATABASE INITIAL PERSISTENCE
    const { data: album, error: dbError } = await supabaseServer
      .from("album_packs")
      .insert({
        dj_id: djProfile.id,
        title,
        description,
        price,
        file_key: tempKey, // Temporary, will be updated after processing
        original_file_key: tempKey,
        upload_method: uploadMethod,
        is_fan_only: isFanOnly,
        processing_status: 'pending',
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (dbError || !album) throw dbError;

    // 5. TRIGGER BACKGROUND PROCESSING
    // In a real prod env, we'd use BullMQ. Here we fire and forget (with caveat on serverless runtime).
    // For this implementation, we proceed to call the processor.
    console.log(`[ALBUM_UPLOAD] Triggering processing for album: ${album.id}`);
    
    // We don't 'await' this to return a quick response to the UI
    AlbumProcessorService.processUploadedZip(
        album.id,
        user.id,
        tempKey,
        coreProfile.full_name,
        title
    ).catch(err => {
        console.error(`[BACKGROUND_PROCESS_FAIL] Album ${album.id}:`, err);
    });

    return ok({
      success: true,
      albumId: album.id,
      status: "processing",
      message: "ZIP uploaded. MixMint metadata injection in progress..."
    });

  } catch (err: unknown) {
    console.error("[ALBUM_UPLOAD_ERROR]:", err);
    const msg = err instanceof Error ? err.message : "Internal server error";
    return fail(msg, 500);
  }
}
