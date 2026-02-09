import { supabaseServer } from "@/lib/supabaseServer";
import { r2 } from "@/lib/r2";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { getDJStoragePath } from "@/lib/djStorage";
import { requireAuth } from "@/lib/requireAuth";
import { requireDJ } from "@/lib/requireDJ";
import { ok, fail } from "@/lib/apiResponse";

/**
 * POST /api/dj/albums/upload
 * Standardized DJ album (ZIP) uploader.
 * Enforces ₹79 minimum price and secure storage.
 */
export async function POST(req: Request) {
  try {
    // 1. AUTH & ROLE CHECK
    const user = await requireAuth();
    await requireDJ(user.id);

    // Verify DJ profile status
    const { data: djProfile, error: profileError } = await supabaseServer
      .from("dj_profiles")
      .select("id, status")
      .eq("id", user.id) // PK is user.id
      .single();

    if (profileError || !djProfile) {
      return fail("DJ profile not found", 403);
    }

    if (djProfile.status !== "approved") {
      return fail("Your DJ account is pending approval", 403);
    }

    // Fetch DJ name from profiles for storage path
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

    // MIME type check (ZIP/RAR/7Z)
    const allowedTypes = ["application/zip", "application/x-zip-compressed", "application/x-rar-compressed", "application/x-7z-compressed"];
    if (!allowedTypes.includes(file.type) && !file.name.endsWith(".zip")) {
      return fail("Only ZIP, RAR, 7Z allowed for album packs", 400);
    }

    // Size check (250MB for Albums)
    const MAX_SIZE = 250 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      return fail("Album ZIP too large (max 250MB)", 400);
    }

    // 3. REMAINING FORM DATA
    const title = formData.get("title") as string;
    const description = formData.get("description") as string;
    const price = Number(formData.get("price"));
    const isFanOnly = formData.get("is_fan_only") === "true";

    if (!title || isNaN(price)) {
      return fail("Missing required fields (title/price)", 400);
    }

    // Enforce platform minimum price (₹79) for album packs
    if (price < 79) {
      return fail("Minimum album pack price is ₹79", 400);
    }

    // 4. STORAGE LOGIC
    const fileName = file.name;
    const fileKey = getDJStoragePath(
      coreProfile.full_name,
      user.id,
      "albums",
      fileName
    );
    const buffer = Buffer.from(await file.arrayBuffer());

    // 5. MANDATORY MIXMINT METADATA (R2 Headers)
    const uploadParams = {
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: fileKey,
      Body: buffer,
      ContentType: file.type || "application/zip",
      Metadata: {
        "x-platform": "MixMint",
        "x-platform-url": "https://mixmint.site",
        "x-upload-source": "MixMint DJ Album Upload",
        "x-dj-id": user.id,
        "x-uploaded-at": new Date().toISOString(),
        "x-is-fan-only": String(isFanOnly),
      },
    };

    await r2.send(new PutObjectCommand(uploadParams));

    // 6. DATABASE PERSISTENCE
    const { error: dbError } = await supabaseServer.from("album_packs").insert({
      dj_id: djProfile.id,
      title,
      description,
      price,
      file_key: fileKey,
      is_fan_only: isFanOnly,
      created_at: new Date().toISOString(),
    });

    if (dbError) throw dbError;

    return ok({
      success: true,
      fileKey,
      type: "zip_pack",
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    if (err.message === "FORBIDDEN") {
      return fail("DJ access required", 403);
    }

    console.error("[ALBUM_UPLOAD_ERROR]:", err);
    return fail(err.message || "Internal server error", 500);
  }
}
