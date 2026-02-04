import { supabaseServer } from "@/app/lib/supabaseServer";
import { r2 } from "@/app/lib/r2";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import { ok, fail } from "@/app/lib/apiResponse";
import { logger } from "@/app/lib/logger";
import { checkRateLimit, getClientIp } from "@/app/lib/rateLimit";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const token = searchParams.get("token");

    if (!token) {
      return fail("Token required", 400, "DOWNLOAD");
    }

    // --- RATE LIMITING ---
    const ip = getClientIp(req);
    const rl = await checkRateLimit("download", ip, 30, 3600); // 30 downloads per hour
    if (!rl.success) {
      return fail("Too many download attempts. Please wait an hour.", 429, "DOWNLOAD");
    }

    // --- STEP 2 & 3: VALIDATE TOKEN ---
    const { data: tokenRow, error } = await supabaseServer
      .from("download_tokens")
      .select("*")
      .eq("token", token)
      .eq("is_used", false) // Ensure it's unused
      .gt("expires_at", new Date().toISOString()) // Ensure it hasn't expired
      .single();

    if (error || !tokenRow) {
      logger.warn("DOWNLOAD", "Invalid/Expired token access attempt", { token, ip });
      return fail("Download token already used or expired", 403, "DOWNLOAD");
    }

    // IP lock (Security layer)
    if (tokenRow.ip_address && tokenRow.ip_address !== ip) {
      logger.warn("DOWNLOAD", "IP mismatch for token", { token, tokenIp: tokenRow.ip_address, clientIp: ip });
      return fail("IP mismatch", 403, "DOWNLOAD");
    }

    // --- FETCH METADATA & STREAM FILE (PHASE H3) ---
    let fileKey = "";
    let fileName = "download";
    let contentType = "application/octet-stream";
    let djId = "";
    let accessSource = tokenRow.access_source;
    let isFanOnly = false;

    if (tokenRow.content_type === "track") {
      const { data: track } = await supabaseServer
        .from("tracks")
        .select("file_key, title, dj_id, is_fan_only") // Added dj_id and is_fan_only
        .eq("id", tokenRow.content_id)
        .single();

      if (!track) throw new Error("CONTENT_NOT_FOUND");
      fileKey = track.file_key;
      fileName = track.title;
      djId = track.dj_id; // Set djId for tracks
      isFanOnly = track.is_fan_only;
    } else if (tokenRow.content_type === "zip") {
      const { data: album } = await supabaseServer
        .from("album_packs")
        .select("file_key, dj_id, title, is_fan_only")
        .eq("id", tokenRow.content_id)
        .single();

      if (!album) throw new Error("CONTENT_NOT_FOUND");
      fileKey = album.file_key;
      fileName = `${album.title || "album"}.zip`;
      contentType = "application/zip";
      djId = album.dj_id;
      isFanOnly = album.is_fan_only;
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
          .select("id, tracks_used, fan_uploads_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", djId)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          const updateData: any = {};
          if (isFanOnly) {
            updateData.fan_uploads_used = (sub.fan_uploads_used || 0) + 1;
          } else {
            updateData.tracks_used = (sub.tracks_used || 0) + 1;
          }
          await supabaseServer
            .from("dj_subscriptions")
            .update(updateData)
            .eq("id", sub.id);
        }
      } else if (tokenRow.content_type === "zip") {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("id, zip_used, fan_uploads_used")
          .eq("user_id", tokenRow.user_id)
          .eq("dj_id", djId)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub) {
          const updateData: any = {};
          if (isFanOnly) {
            updateData.fan_uploads_used = (sub.fan_uploads_used || 0) + 1;
          } else {
            updateData.zip_used = (sub.zip_used || 0) + 1;
          }
          await supabaseServer
            .from("dj_subscriptions")
            .update(updateData)
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
      return fail("Content not found", 404, "DOWNLOAD");
    }
    logger.error("DOWNLOAD", "Download catastrophic failure", err);
    return fail(err.message || "Internal server error", 500, "DOWNLOAD");
  }
}
