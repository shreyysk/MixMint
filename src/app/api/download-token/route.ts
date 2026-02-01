import { NextResponse } from "next/server";
import crypto from "crypto";
import { supabaseServer } from "@/app/lib/supabaseServer";

export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const tokenValue = authHeader.replace("Bearer ", "");

    // Verify user via Supabase auth
    const { data: userData, error: authError } =
      await supabaseServer.auth.getUser(tokenValue);

    if (authError || !userData?.user) {
      return NextResponse.json({ error: "Invalid session" }, { status: 401 });
    }

    const body = await req.json();
    const { content_id, content_type } = body;

    if (!content_id || !content_type) {
      return NextResponse.json(
        { error: "content_id and content_type required" },
        { status: 400 }
      );
    }

    // Enforce ownership/access for tracks
    if (content_type === "track") {
      // 1. We need the DJ ID to check subscriptions later
      const { data: track, error: trackError } = await supabaseServer
        .from("tracks")
        .select("dj_id")
        .eq("id", content_id)
        .single();

      if (trackError || !track) {
        return NextResponse.json({ error: "Track not found" }, { status: 404 });
      }

      // 2. Check Purchase first
      const { data: purchases } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", userData.user.id)
        .eq("content_id", content_id)
        .eq("content_type", "track")
        .limit(1);

      const isPurchased = purchases && purchases.length > 0;

      // 3. If NOT purchased, check Subscription
      if (!isPurchased) {
        const { data: subscription } = await supabaseServer
          .from("dj_subscriptions")
          .select("*")
          .eq("user_id", userData.user.id)
          .eq("dj_id", track.dj_id)
          .gt("expires_at", new Date().toISOString())
          .limit(1)
          .single();

        if (!subscription) {
          return NextResponse.json(
            { error: "Access denied. Purchase this track or subscribe to the DJ." },
            { status: 403 }
          );
        }

        if (subscription.tracks_used >= subscription.track_quota) {
          return NextResponse.json(
            { error: "Subscription track quota exhausted" },
            { status: 403 }
          );
        }

        await supabaseServer
          .from("dj_subscriptions")
          .update({ tracks_used: subscription.tracks_used + 1 })
          .eq("id", subscription.id);
      }
    }

    // Enforce ownership/access for ZIPs (PHASE 3.3)
    if (content_type === "zip") {
      const { data: album, error: albumError } = await supabaseServer
        .from("album_packs")
        .select("id, dj_id, price")
        .eq("id", content_id)
        .single();

      if (albumError || !album) {
        return NextResponse.json({ error: "Album not found" }, { status: 404 });
      }

      // 1️⃣ Check purchase
      const { data: purchase } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", userData.user.id)
        .eq("content_type", "zip")
        .eq("content_id", album.id)
        .single();

      let allowed = !!purchase;

      // 2️⃣ If not purchased → check subscription ZIP quota
      if (!allowed) {
        const { data: sub } = await supabaseServer
          .from("dj_subscriptions")
          .select("*")
          .eq("user_id", userData.user.id)
          .eq("dj_id", album.dj_id)
          .gt("expires_at", new Date().toISOString())
          .single();

        if (!sub || sub.zip_used >= sub.zip_quota) {
          return NextResponse.json(
            { error: "ZIP quota exceeded or no subscription" },
            { status: 403 }
          );
        }

        allowed = true;
      }

      if (!allowed) {
        return NextResponse.json(
          { error: "Access denied" },
          { status: 403 }
        );
      }

      // ✅ Token will be created below
      // 📌 We do NOT increment zip_used yet - happens after successful download
    }

    // Generate secure token
    const downloadToken = crypto.randomBytes(32).toString("hex");

    // Expire in 5 minutes
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString();

    const { error: insertError } = await supabaseServer
      .from("download_tokens")
      .insert({
        user_id: userData.user.id,
        content_id,
        content_type,
        token: downloadToken,
        expires_at: expiresAt,
      });

    if (insertError) {
      return NextResponse.json({ error: insertError.message }, { status: 500 });
    }

    return NextResponse.json({
      token: downloadToken,
      expires_at: expiresAt,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}