import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { r2 } from "@/app/lib/r2";
import { GetObjectCommand } from "@aws-sdk/client-s3";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const token = searchParams.get("token");

    if (!token) {
      return NextResponse.json({ error: "Token required" }, { status: 400 });
    }

    // Get client IP
    const ip =
      req.headers.get("x-forwarded-for")?.split(",")[0] ||
      req.headers.get("x-real-ip") ||
      "unknown";

    // --- STEP 2 & 3: VALIDATE TOKEN ---
    const { data: tokenRow, error } = await supabaseServer
      .from("download_tokens")
      .select("*")
      .eq("token", token)
      .eq("is_used", false) // Ensure it's unused
      .gt("expires_at", new Date().toISOString()) // Ensure it hasn't expired
      .single();

    if (error || !tokenRow) {
      return NextResponse.json(
        { error: "Download token already used or expired" },
        { status: 403 }
      );
    }

    // IP lock (Security layer)
    if (tokenRow.ip_address && tokenRow.ip_address !== ip) {
      return NextResponse.json(
        { error: "IP mismatch" },
        { status: 403 }
      );
    }

    // --- FETCH METADATA & STREAM FILE (PHASE H3) ---
    let fileKey = "";
    let fileName = "download";
    let contentType = "application/octet-stream";
    let djId = "";

    if (tokenRow.content_type === "track") {
      const { data: track } = await supabaseServer
        .from("tracks")
        .select("file_key, title")
        .eq("id", tokenRow.content_id)
        .single();

      if (!track) throw new Error("CONTENT_NOT_FOUND");
      fileKey = track.file_key;
      fileName = track.title;
    } else if (tokenRow.content_type === "zip") {
      const { data: album } = await supabaseServer
        .from("album_packs")
        .select("file_key, dj_id, title")
        .eq("id", tokenRow.content_id)
        .single();

      if (!album) throw new Error("CONTENT_NOT_FOUND");
      fileKey = album.file_key;
      fileName = `${album.title || "album"}.zip`;
      contentType = "application/zip";
      djId = album.dj_id;
    } else {
      throw new Error("INVALID_CONTENT_TYPE");
    }

    // 1️⃣ Initialize R2 stream first
    const object = await r2.send(new GetObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: fileKey,
    }));

    // 2️⃣ ATOMIC UPDATE: Mark token used only after stream is ready
    await supabaseServer
      .from("download_tokens")
      .update({ is_used: true })
      .eq("id", tokenRow.id);

    // 3️⃣ QUOTA INCREMENT (Subscription-based ZIPs only)
    if (tokenRow.content_type === "zip") {
      const { data: purchase } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", tokenRow.user_id)
        .eq("content_type", "zip")
        .eq("content_id", tokenRow.content_id)
        .single();

      if (!purchase) {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("zip_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", djId)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          await supabaseServer
            .from("dj_subscriptions")
            .update({ zip_used: (sub.zip_used || 0) + 1 })
            .eq("user_id", tokenRow.user_id)
            .eq("dj_id", djId);
        }
      }
    }

    // 4️⃣ Return stream
    return new Response(object.Body as any, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${fileName}"`,
      },
    });

  } catch (err: any) {
    if (err.message === "CONTENT_NOT_FOUND") {
      return NextResponse.json({ error: "Content not found" }, { status: 404 });
    }
    console.error("Download Error:", err);
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
