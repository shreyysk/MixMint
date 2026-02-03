import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { SUBSCRIPTION_PLANS, SubscriptionPlan } from "@/app/lib/subscriptionPlans";

/**
 * @deprecated This API is deprecated and should not be used directly.
 * 
 * SECURITY WARNING: This endpoint creates subscriptions WITHOUT payment verification.
 * 
 * New subscription flow:
 * 1. POST /api/payment/create (with content_type: "subscription")
 * 2. Complete payment via Razorpay/PhonePe
 * 3. POST /api/payment/verify (verify & create subscription)
 * 
 * This endpoint is kept for backwards compatibility only.
 */
export async function POST(req: Request) {
  // Return deprecation warning
  return NextResponse.json(
    { 
      error: "This API is deprecated. Use /api/payment/create and /api/payment/verify instead.",
      deprecated: true,
      new_flow: {
        step1: "POST /api/payment/create with content_type: 'subscription'",
        step2: "Complete payment",
        step3: "POST /api/payment/verify"
      }
    },
    { status: 410 } // Gone
  );

  /* ORIGINAL CODE - DISABLED FOR SECURITY
export async function POST_DISABLED(req: Request) {
  console.log("SUBSCRIBE API HIT");

  try {
    const authHeader = req.headers.get("authorization");
    console.log("AUTH HEADER:", authHeader);

    if (!authHeader) {
      console.log("NO AUTH HEADER");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.replace("Bearer ", "");
    console.log("TOKEN LENGTH:", token.length);

    const authResult = await supabaseServer.auth.getUser(token);
    console.log("AUTH RESULT:", authResult);

    const user = authResult.data.user;

    if (!user) {
      console.log("NO USER FROM TOKEN");
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    console.log("BODY:", body);

    const { dj_id, plan } = body as { dj_id: string; plan: SubscriptionPlan };

    if (!SUBSCRIPTION_PLANS[plan]) {
      console.log("INVALID PLAN");
      return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    const planConfig = SUBSCRIPTION_PLANS[plan];

    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + planConfig.duration_days);

    const insertResult = await supabaseServer
      .from("dj_subscriptions")
      .insert({
        user_id: user.id,
        dj_id,
        plan,
        track_quota: planConfig.track_quota,
        zip_quota: planConfig.zip_quota,
        fan_upload_quota: planConfig.fan_upload_quota,
        expires_at: expiresAt.toISOString(),
      });

    console.log("INSERT RESULT:", insertResult);

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("SUBSCRIBE API ERROR:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
