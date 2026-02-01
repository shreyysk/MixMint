import { NextResponse } from "next/server";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2 } from "@/app/lib/r2";
import { supabaseServer } from "@/app/lib/supabaseServer";

/**
 * POST /api/upload
 * 
 * General file uploader for DJs and Admins.
 * Standardized with MixMint platform metadata and storage isolation.
 */
export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.replace("Bearer ", "");
    const { data: { user }, error: authError } = await supabaseServer.auth.getUser(token);

    if (authError || !user) {
      return NextResponse.json({ error: "Invalid session" }, { status: 401 });
    }

    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "dj" && profile?.role !== "admin") {
      return NextResponse.json({ error: "Unprivileged role" }, { status: 403 });
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    // Standardized extensions check
    const fileName = file.name;
    const fileExt = fileName.split(".").pop()?.toLowerCase();
    const isZip = ["zip", "rar", "7z"].includes(fileExt || "");
    const folder = isZip ? "zips" : "tracks";

    const buffer = Buffer.from(await file.arrayBuffer());
    const timestamp = Date.now();
    const fileKey = `${folder}/${user.id}/${timestamp}-${fileName}`;

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
    console.error("[GENERAL_UPLOAD_ERROR]:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}