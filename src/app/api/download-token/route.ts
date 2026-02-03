import crypto from "crypto";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { ok, fail } from "@/app/lib/apiResponse";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();

    const body = await req.json();
    const { content_id, content_type } = body;

    if (!content_id || !content_type) {
      return fail("content_id and content_type required", 400);
    }

    let access_source: "purchase" | "subscription" | null = null;
    let djId = "";

    if (content_type === "track") {
      const { data: track, error: trackError } = await supabaseServer
        .from("tracks")
        .select("dj_id")
        .eq("id", content_id)
        .single();

      if (trackError || !track) {
        return fail("Track not found", 404);
      }
      djId = track.dj_id;

      // 1. Check Purchase first
      const { data: purchases } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", user.id)
        .eq("content_id", content_id)
        .eq("content_type", "track")
        .limit(1);

      if (purchases && purchases.length > 0) {
        access_source = "purchase";
      } else {
        // 2. If NOT purchased, check Subscription
        const { data: subscription } = await supabaseServer
          .from("dj_subscriptions")
          .select("*")
          .eq("user_id", user.id)
          .eq("dj_id", track.dj_id)
          .gt("expires_at", new Date().toISOString())
          .limit(1)
          .single();

        if (subscription && subscription.tracks_used < subscription.track_quota) {
          access_source = "subscription";
        }
      }
    } else if (content_type === "zip") {
      const { data: album, error: albumError } = await supabaseServer
        .from("album_packs")
        .select("id, dj_id")
        .eq("id", content_id)
        .single();

      if (albumError || !album) {
        return fail("Album not found", 404);
      }
      djId = album.dj_id;

      // 1. Check Purchase first
      const { data: purchase } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", user.id)
        .eq("content_type", "zip")
        .eq("content_id", album.id)
        .single();

      if (purchase) {
        access_source = "purchase";
      } else {
        // 2. If not purchased -> check subscription ZIP quota
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("*")
          .eq("user_id", user.id)
          .eq("dj_id", album.dj_id)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (sub && sub.zip_used < sub.zip_quota) {
          access_source = "subscription";
        }
      }
    }

    if (!access_source) {
      return fail("Access denied. Purchase this content or subscribe to the DJ.", 403);
    }

    // Generate secure token
    const downloadToken = crypto.randomBytes(32).toString("hex");

    // Expire in 5 minutes
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString();

    const { error: insertError } = await supabaseServer
      .from("download_tokens")
      .insert({
        user_id: user.id,
        content_id,
        content_type,
        token: downloadToken,
        expires_at: expiresAt,
        access_source, // persisted guard (B1.2)
      });

    if (insertError) {
      return fail(insertError.message, 500);
    }

    return ok({
      token: downloadToken,
      expires_at: expiresAt,
    });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    console.error("[DOWNLOAD_TOKEN_ERROR]", err);
    return fail(err.message, 500);
  }
}