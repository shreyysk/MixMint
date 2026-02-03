import { NextResponse } from "next/server";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2 } from "@/app/lib/r2";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { getDJStoragePath } from "@/app/lib/djStorage";
import { requireAuth } from "@/app/lib/requireAuth";

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
      return NextResponse.json({ error: "Unprivileged role" }, { status: 403 });
    }

    if (!profile?.full_name) {
      return NextResponse.json({ error: "Profile incomplete: full_name required" }, { status: 400 });
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "No file provided or invalid file input" }, { status: 400 });
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

    return NextResponse.json({
      success: true,
      fileKey,
      fileName: file.name,
      contentType: file.type,
    });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    console.error("[GENERAL_UPLOAD_ERROR]:", err);
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}