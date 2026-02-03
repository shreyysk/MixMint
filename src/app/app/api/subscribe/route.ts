import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { subscriptionPlans } from "@/app/lib/subscriptionPlans";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const body = await req.json();

    const { dj_id, plan } = body;

    if (!dj_id || !plan || !subscriptionPlans[plan]) {
      return NextResponse.json(
        { error: "Invalid subscription request" },
        { status: 400 }
      );
    }

    const planConfig = subscriptionPlans[plan];
    const now = new Date();
    const expiresAt = new Date(
      now.getTime() + planConfig.durationDays * 24 * 60 * 60 * 1000
    );

    // Check existing subscription
    const { data: existing } = await supabaseServer
      .from("dj_subscriptions")
      .select("*")
      .eq("user_id", user.id)
      .eq("dj_id", dj_id)
      .single();

    // 🔁 RENEW
    if (existing) {
      const { error } = await supabaseServer
        .from("dj_subscriptions")
        .update({
          plan,
          track_quota: planConfig.trackQuota,
          zip_quota: planConfig.zipQuota,
          fan_upload_quota: planConfig.fanUploadQuota,
          tracks_used: 0,
          zips_used: 0,
          fan_uploads_used: 0,
          starts_at: now.toISOString(),
          expires_at: expiresAt.toISOString(),
        })
        .eq("id", existing.id);

      if (error) {
        console.error("[SUB_RENEW_ERROR]", error);
        return NextResponse.json(
          { error: "Subscription renewal failed" },
          { status: 500 }
        );
      }

      return NextResponse.json({ success: true, renewed: true });
    }

    // 🆕 NEW SUBSCRIPTION
    const { error } = await supabaseServer
      .from("dj_subscriptions")
      .insert({
        user_id: user.id,
        dj_id,
        plan,
        track_quota: planConfig.trackQuota,
        zip_quota: planConfig.zipQuota,
        fan_upload_quota: planConfig.fanUploadQuota,
        tracks_used: 0,
        zips_used: 0,
        fan_uploads_used: 0,
        starts_at: now.toISOString(),
        expires_at: expiresAt.toISOString(),
      });

    if (error) {
      console.error("[SUB_CREATE_ERROR]", error);
      return NextResponse.json(
        { error: "Subscription creation failed" },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true, created: true });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    console.error("[SUB_FATAL]", err);
    return NextResponse.json(
      { error: "Server error" },
      { status: 500 }
    );
  }
}
