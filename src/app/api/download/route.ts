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

    // Fetch token record
    const { data: tokenRow } = await supabaseServer
      .from("download_tokens")
      .select("*")
      .eq("token", token)
      .limit(1)
      .single();

    if (!tokenRow) {
      return NextResponse.json({ error: "Invalid token" }, { status: 403 });
    }

    // Expiry check
    if (new Date(tokenRow.expires_at) < new Date()) {
      return NextResponse.json({ error: "Token expired" }, { status: 403 });
    }

    // Attempt limit
    if (tokenRow.attempts >= tokenRow.max_attempts) {
      return NextResponse.json(
        { error: "Download limit exceeded" },
        { status: 403 }
      );
    }

    // IP lock
    if (tokenRow.ip_address && tokenRow.ip_address !== ip) {
      return NextResponse.json(
        { error: "IP mismatch" },
        { status: 403 }
      );
    }

    // Fetch content metadata
    const { data: track } = await supabaseServer
      .from("tracks")
      .select("file_key, title")
      .eq("id", tokenRow.content_id)
      .single();

    if (!track) {
      return NextResponse.json({ error: "Content not found" }, { status: 404 });
    }

    if (tokenRow.is_used) {
    return NextResponse.json(
        { error: "Download token already used" },
        { status: 403 }
    );
    }

    // Update token usage
    const { error: updateError } = await supabaseServer
    .from("download_tokens")
    .update({
        attempts: tokenRow.attempts + 1,
        ip_address: tokenRow.ip_address ?? ip,
        is_used: tokenRow.attempts + 1 >= tokenRow.max_attempts,
    })
    .eq("id", tokenRow.id)
    .eq("attempts", tokenRow.attempts); // optimistic lock

    if (updateError) {
    return NextResponse.json(
        { error: "Download token already used or expired" },
        { status: 403 }
    );
    }

    // Stream from R2
    const command = new GetObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: track.file_key,
    });

    const object = await r2.send(command);

    return new Response(object.Body as any, {
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": `attachment; filename="${track.title}"`,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
