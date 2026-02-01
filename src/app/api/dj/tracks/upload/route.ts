import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { r2 } from "@/app/lib/r2";
import { PutObjectCommand } from "@aws-sdk/client-s3";

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
    // 1. AUTHENTICATION & ROLE CHECK
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.replace("Bearer ", "");
    const { data: { user } } = await supabaseServer.auth.getUser(token);

    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Verify DJ profile and approval status
    const { data: djProfile, error: profileError } = await supabaseServer
      .from("dj_profiles")
      .select("id, status")
      .eq("user_id", user.id)
      .single();

    if (profileError || !djProfile) {
      return NextResponse.json(
        { error: "DJ profile not found" },
        { status: 403 }
      );
    }

    if (djProfile.status !== "approved") {
      return NextResponse.json(
        { error: "Your DJ account is pending approval" },
        { status: 403 }
      );
    }

    // 2. FILE VALIDATION
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
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
    const timestamp = Date.now();
    // Path: tracks/{user_id}/{timestamp}-{filename}
    const fileKey = `tracks/${user.id}/${timestamp}-${fileName}`;
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
    console.error("[DJ_UPLOAD_ERROR]:", err);
    return NextResponse.json(
      { error: err.message || "Internal server error" },
      { status: 500 }
    );
  }
}