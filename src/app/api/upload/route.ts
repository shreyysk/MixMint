import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2 } from "@/lib/r2";
import { supabaseServer } from "@/lib/supabaseServer";
import { getDJStoragePath } from "@/lib/djStorage";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * POST /api/upload
 * 
 * General file uploader for DJs and Admins.
 * Standardized with MixMint platform metadata and storage isolation.
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();

    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role, full_name")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "dj" && profile?.role !== "admin") {
      return fail("Unprivileged role", 403);
    }

    if (!profile?.full_name) {
      return fail("Profile incomplete: full_name required", 400);
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file || !(file instanceof File)) {
      return fail("No file provided or invalid file input", 400);
    }

    // Standardized extensions check
    const fileName = file.name;
    const fileExt = fileName.split(".").pop()?.toLowerCase();
    const isZip = ["zip", "rar", "7z"].includes(fileExt || "");
    const folder = isZip ? "zips" : "tracks";

    const buffer = Buffer.from(await file.arrayBuffer());
    // NEW PATH FORMAT: <dj_slug>_<dj_id>/tracks|albums/<timestamp>-<filename>
    const fileKey = getDJStoragePath(
      profile.full_name,
      user.id,
      isZip ? "albums" : "tracks",
      fileName
    );

    // MANDATORY MIXMINT METADATA
    const metadata = {
      "x-platform": "MixMint",
      "x-platform-url": "https://mixmint.site",
      "x-upload-source": "MixMint DJ Upload",
      "x-dj-id": user.id,
      "x-uploaded-at": new Date().toISOString(),
    };

    await r2.send(
      new PutObjectCommand({
        Bucket: process.env.R2_BUCKET_NAME!,
        Key: fileKey,
        Body: buffer,
        ContentType: file.type || "application/octet-stream",
        Metadata: metadata,
      })
    );

    return ok({
      success: true,
      fileKey,
      fileName: file.name,
      contentType: file.type,
    });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    console.error("[GENERAL_UPLOAD_ERROR]:", err);
    return fail(err.message || "Internal server error", 500);
  }
}