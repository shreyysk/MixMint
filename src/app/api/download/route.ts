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

    // --- HANDLE TRACK DOWNLOADS ---
    if (tokenRow.content_type === "track") {
      const { data: track } = await supabaseServer
        .from("tracks")
        .select("file_key, title")
        .eq("id", tokenRow.content_id)
        .single();

      if (!track) {
        return NextResponse.json({ error: "Content not found" }, { status: 404 });
      }

      // Get file from R2
      const object = await r2.send(new GetObjectCommand({
        Bucket: process.env.R2_BUCKET_NAME!,
        Key: track.file_key,
      }));

      // Mark token used
      await supabaseServer
        .from("download_tokens")
        .update({ is_used: true })
        .eq("id", tokenRow.id);

      // Return file stream
      return new Response(object.Body as any, {
        headers: {
          "Content-Type": "application/octet-stream",
          "Content-Disposition": `attachment; filename="${track.title}"`,
        },
      });
    }

    // --- HANDLE ZIP DOWNLOADS (PHASE 3.3) ---
    if (tokenRow.content_type === "zip") {
      const { data: album } = await supabaseServer
        .from("album_packs")
        .select("file_key, dj_id, title")
        .eq("id", tokenRow.content_id)
        .single();

      if (!album) {
        return NextResponse.json({ error: "Album not found" }, { status: 404 });
      }

      // Get ZIP from R2
      const object = await r2.send(new GetObjectCommand({
        Bucket: process.env.R2_BUCKET_NAME!,
        Key: album.file_key,
      }));

      // Mark token used (critical security step)
      await supabaseServer
        .from("download_tokens")
        .update({ is_used: true })
        .eq("id", tokenRow.id);

      // Increment ZIP quota if subscription-based (not purchase)
      // Check if this was a subscription download
      const { data: purchase } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", tokenRow.user_id)
        .eq("content_type", "zip")
        .eq("content_id", tokenRow.content_id)
        .single();

      // If no purchase found, this was a subscription download → increment quota
      if (!purchase) {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("zip_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", album.dj_id)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          await supabaseServer
            .from("dj_subscriptions")
            .update({ zip_used: (sub.zip_used || 0) + 1 })
            .eq("user_id", tokenRow.user_id)
            .eq("dj_id", album.dj_id);
        }
      }

      // Return ZIP stream
      return new Response(object.Body as any, {
        headers: {
          "Content-Type": "application/zip",
          "Content-Disposition": `attachment; filename="${album.title || 'album'}.zip"`,
        },
      });
    }

    return NextResponse.json({ error: "Invalid content type" }, { status: 400 });

  } catch (err: any) {
    console.error("Download Error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
