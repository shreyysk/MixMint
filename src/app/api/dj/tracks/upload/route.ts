import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { r2 } from "@/app/lib/r2";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { getDJStoragePath } from "@/app/lib/djStorage";
import { requireAuth } from "@/app/lib/requireAuth";
import { requireDJ } from "@/app/lib/requireDJ";

/**
 * GET /api/dj/tracks/upload
 * Returns a status message for browser verification.
 */
export async function GET() {
  return NextResponse.json({ message: "DJ Tracks Upload API is active. Use POST to upload audio files." });
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
      .eq("user_id", user.id)
      .single();

    if (profileError || !djProfile) {
      return NextResponse.json({ error: "DJ profile not found" }, { status: 403 });
    }

    if (djProfile.status !== "approved") {
      return NextResponse.json({ error: "Your DJ account is pending approval" }, { status: 403 });
    }

    // Fetch DJ full_name from profiles for storage path
    const { data: coreProfile, error: coreError } = await supabaseServer
      .from("profiles")
      .select("full_name")
      .eq("id", user.id)
      .single();

    if (coreError || !coreProfile || !coreProfile.full_name) {
      return NextResponse.json({ error: "Profile incomplete: full_name required" }, { status: 400 });
    }

    // 2. FILE VALIDATION
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "No file uploaded or invalid file input" }, { status: 400 });
    }

    // MIME type check
    const allowedTypes = ["audio/mpeg", "audio/wav", "audio/flac"];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: "Only MP3, WAV, FLAC allowed" },
        { status: 400 }
      );
    }

    // Size check (50MB)
    const MAX_SIZE = 50 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      return NextResponse.json(
        { error: "File too large (max 50MB)" },
        { status: 400 }
      );
    }

    // 3. REMAINING FORM DATA
    const title = formData.get("title") as string;
    const price = Number(formData.get("price"));
    const contentType = (formData.get("content_type") as "track" | "zip") || "track";

    if (!title || isNaN(price)) {
      return NextResponse.json(
        { error: "Missing required fields (title/price)" },
        { status: 400 }
      );
    }

    // 4. STORAGE LOGIC
    const fileName = file.name;
    // NEW PATH FORMAT: <dj_slug>_<dj_id>/tracks/<timestamp>-<filename>
    const fileKey = getDJStoragePath(
      coreProfile.full_name,
      user.id,
      "tracks",
      fileName
    );
    const buffer = Buffer.from(await file.arrayBuffer());

    // 5. MANDATORY MIXMINT METADATA
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
      },
    };

    await r2.send(new PutObjectCommand(uploadParams));

    // 6. DATABASE PERSISTENCE (PHASE 3)
    const { error: dbError } = await supabaseServer.from("tracks").insert({
      dj_id: djProfile.id,
      title,
      price,
      file_key: fileKey,
      created_at: new Date().toISOString(),
    });

    if (dbError) throw dbError;

    return NextResponse.json({
      success: true,
      fileKey,
      type: contentType,
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    if (err.message === "FORBIDDEN") {
      return NextResponse.json({ error: "DJ access required" }, { status: 403 });
    }

    console.error("[DJ_UPLOAD_ERROR]:", err);
    return NextResponse.json(
      { error: err.message || "Internal server error" },
      { status: 500 }
    );
  }
}