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

    // Enforce ownership for tracks
    if (content_type === "track") {
    const { data: purchases, error } = await supabaseServer
    .from("purchases")
    .select("id")
    .eq("user_id", userData.user.id)
    .eq("content_id", content_id)
    .eq("content_type", "track")
    .limit(1);

    if (error || !purchases || purchases.length === 0) {
    return NextResponse.json(
        { error: "You do not own this track" },
        { status: 403 }
    );
    }
    }

    if (!content_id || !content_type) {
    return NextResponse.json(
        { error: "content_id and content_type required" },
        { status: 400 }
    );
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
