import { supabaseServer } from "@/lib/supabaseServer";
import { r2 } from "@/lib/r2";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { getDJStoragePath } from "@/lib/djStorage";
import { requireAuth } from "@/lib/requireAuth";
import { requireDJ } from "@/lib/requireDJ";
import { ok, fail } from "@/lib/apiResponse";
import { validatePreviewUrl } from "@/lib/previewUtils";

/**
 * GET /api/dj/tracks/upload
 * Returns a status message for browser verification.
 */
export async function GET() {
  return ok({ message: "DJ Tracks Upload API is active. Use POST to upload audio files." });
}

/**
 * POST /api/dj/tracks/upload
 * * Standardized DJ track uploader.
 * Includes MixMint platform metadata and storage isolation.
 * NOTE: Database insertion is disabled for this phase.
 */
export async function POST(req: Request) {
  try {
    // 1. AUTHENTICATION & ROLE CHECK (PHASE H1)
    const user = await requireAuth();
    await requireDJ(user.id);

    // Verify DJ profile status for approval
    const { data: djProfile, error: profileError } = await supabaseServer
      .from("dj_profiles")
      .select("id, status")
      .eq("id", user.id)
      .single();

    if (profileError || !djProfile) {
      return fail("DJ profile not found", 403);
    }

    if (djProfile.status !== "approved") {
      return fail("Your DJ account is pending approval", 403);
    }

    // Fetch DJ full_name from profiles for storage path
    const { data: coreProfile, error: coreError } = await supabaseServer
      .from("profiles")
      .select("full_name")
      .eq("id", user.id)
      .single();

    if (coreError || !coreProfile || !coreProfile.full_name) {
      return fail("Profile incomplete: full_name required", 400);
    }

    // 2. FILE VALIDATION
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file || !(file instanceof File)) {
      return fail("No file uploaded or invalid file input", 400);
    }

    // MIME type check
    const allowedTypes = ["audio/mpeg", "audio/wav", "audio/flac"];
    if (!allowedTypes.includes(file.type)) {
      return fail("Only MP3, WAV, FLAC allowed", 400);
    }

    // Size check (50MB) - Platform limit
    const MAX_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      return fail("File too large (max 50MB)", 400);
    }

    // 3. REMAINING FORM DATA
    const title = formData.get("title") as string;
    const price = Number(formData.get("price"));
    const isFanOnly = formData.get("is_fan_only") === "true";
    const bpm = Number(formData.get("bpm")) || null;
    const genre = formData.get("genre") as string || null;
    const versionType = (formData.get("version_type") as string) || "original";
    const youtubeUrl = formData.get("youtube_url") as string || null;
    const instagramUrl = formData.get("instagram_url") as string || null;

    if (!title || isNaN(price)) {
      return fail("Missing required fields (title/price)", 400);
    }

    // Enforce platform minimum price (₹29) for paid tracks
    // Exception: isFanOnly content is not individually purchasable, but we record it.
    if (!isFanOnly && price > 0 && price < 29) {
      return fail("Minimum track price is ₹29", 400);
    }

    // 4. STORAGE LOGIC
    // 5. STORAGE LOGIC (Audio)
    const fileName = file.name;
    const fileKey = getDJStoragePath(
      coreProfile.full_name,
      user.id,
      "tracks",
      fileName
    );
    const buffer = Buffer.from(await file.arrayBuffer());

    // 5b. STORAGE LOGIC (Cover Art)
    const coverFile = formData.get("cover_file") as File;
    let coverUrl = null;

    if (coverFile && coverFile instanceof File) {
        // Simple validation
        if (coverFile.size < 5 * 1024 * 1024 && coverFile.type.startsWith("image/")) {
             const coverKey = getDJStoragePath(
                coreProfile.full_name,
                user.id,
                "covers",
                `cover_${Date.now()}_${coverFile.name}`
             );
             const coverBuffer = Buffer.from(await coverFile.arrayBuffer());
             
             await r2.send(new PutObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: coverKey,
                Body: coverBuffer,
                ContentType: coverFile.type,
                Metadata: { "x-dj-id": user.id }
             }));

             // Public URL (Assuming R2 public access or worker)
             // For now, store the R2 Key or a constructed URL if using a domain
             // We'll store the Key or full URL. Let's assume a public domain env var or standard R2 pattern.
             // If implicit, we can reconstruct. Let's store the Key for consistent backend use, 
             // OR arguably formatting it as a URL is better for frontend.
             // Let's assume we have a public domain variable or we just use the Key for now?
             // Actually, TrackCard expects a URL.
             // Let's assume https://pub-xxxxxxxx.r2.dev/{key} pattern or similar.
             // For safety, I'll store the relative path/key, and we rely on a helper to serve it?
             // Checks Steps 247: <img src={coverUrl} ... />. It expects a full URL.
             // Let's construct it.
             const R2_PUBLIC_DOMAIN = process.env.NEXT_PUBLIC_R2_DOMAIN || "https://cdn.mixmint.site";
             coverUrl = `${R2_PUBLIC_DOMAIN}/${coverKey}`;
        }
    }

    // 5c. MANDATORY MIXMINT METADATA (R2 Headers)
    const uploadParams = {
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: fileKey,
      Body: buffer,
      ContentType: file.type,
      Metadata: {
        "x-platform": "MixMint",
        "x-platform-url": "https://mixmint.site",
        "x-upload-source": "MixMint DJ Tracks Upload",
        "x-dj-id": user.id,
        "x-uploaded-at": new Date().toISOString(),
        "x-is-fan-only": String(isFanOnly),
      },
    };

    await r2.send(new PutObjectCommand(uploadParams));

    // 6. DATABASE PERSISTENCE
    const { error: dbError } = await supabaseServer.from("tracks").insert({
      dj_id: djProfile.id,
      title,
      price,
      file_key: fileKey,
      is_fan_only: isFanOnly,
      bpm,
      genre,
      version_type: versionType,
      cover_url: coverUrl,
      created_at: new Date().toISOString(),
    });

    if (dbError) throw dbError;

    // 7. PREVIEW PERSISTENCE
    const { data: newTrack } = await supabaseServer
      .from("tracks")
      .select("id")
      .eq("file_key", fileKey)
      .single();

    if (newTrack) {
      const previewInserts = [];
      
      if (youtubeUrl) {
        const validated = validatePreviewUrl(youtubeUrl);
        if (validated.type === "youtube") {
          previewInserts.push({
            track_id: newTrack.id,
            preview_type: "youtube",
            url: youtubeUrl,
            embed_id: validated.id,
            is_primary: true
          });
        }
      }

      if (instagramUrl) {
        const validated = validatePreviewUrl(instagramUrl);
        if (validated.type === "instagram") {
          previewInserts.push({
            track_id: newTrack.id,
            preview_type: "instagram",
            url: instagramUrl,
            embed_id: validated.id,
            is_primary: previewInserts.length === 0
          });
        }
      }

      if (previewInserts.length > 0) {
        const { error: previewError } = await supabaseServer
          .from("track_previews")
          .insert(previewInserts);
          
        if (previewError) {
          console.warn("[PREVIEW_SAVE_ERROR]:", previewError);
          // Don't fail the whole upload if just previews fail
        }
      }
    }

    return ok({
      success: true,
      fileKey,
      type: isFanOnly ? "fan_upload" : "track",
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    if (err.message === "FORBIDDEN") {
      return fail("DJ access required", 403);
    }

    console.error("[TRACK_UPLOAD_ERROR]:", err);
    return fail(err.message || "Internal server error", 500);
  }
}