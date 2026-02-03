import { supabaseServer } from "@/app/lib/supabaseServer";
import { r2 } from "@/app/lib/r2";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import { ok, fail } from "@/app/lib/apiResponse";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const token = searchParams.get("token");

    if (!token) {
      return fail("Token required", 400);
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
      return fail("Download token already used or expired", 403);
    }

    // IP lock (Security layer)
    if (tokenRow.ip_address && tokenRow.ip_address !== ip) {
      return fail("IP mismatch", 403);
    }

    // --- FETCH METADATA & STREAM FILE (PHASE H3) ---
    let fileKey = "";
    let fileName = "download";
    let contentType = "application/octet-stream";
    let djId = "";
    let accessSource = tokenRow.access_source;

    if (tokenRow.content_type === "track") {
      const { data: track } = await supabaseServer
        .from("tracks")
        .select("file_key, title, dj_id") // Added dj_id here
        .eq("id", tokenRow.content_id)
        .single();

      if (!track) throw new Error("CONTENT_NOT_FOUND");
      fileKey = track.file_key;
      fileName = track.title;
      djId = track.dj_id; // Set djId for tracks
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

    // 3️⃣ QUOTA INCREMENT (Subscription-based downloads only)
    if (accessSource === "subscription") {
      if (tokenRow.content_type === "track") {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("id, tracks_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", djId)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          await supabaseServer
            .from("dj_subscriptions")
            .update({ tracks_used: (sub.tracks_used || 0) + 1 })
            .eq("id", sub.id);
        }
      } else if (tokenRow.content_type === "zip") {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("id, zip_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", djId)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          await supabaseServer
            .from("dj_subscriptions")
            .update({ zip_used: (sub.zip_used || 0) + 1 })
            .eq("id", sub.id);
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
      return fail("Content not found", 404);
    }
    console.error("[DOWNLOAD_ERROR]", err);
    return fail(err.message || "Internal server error", 500);
  }
}
