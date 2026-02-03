import { NextResponse } from "next/server";
import { requireAuth } from "@/app/lib/requireAuth";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { getPaymentProvider } from "@/app/lib/payments";
import { ok, fail } from "@/app/lib/apiResponse";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const body = await req.json();

    const { content_type, content_id, plan } = body;

    if (!content_type || !content_id) {
      return fail("content_type and content_id are required", 400);
    }

    // Validate content type
    if (!["track", "zip", "subscription"].includes(content_type)) {
      return fail("Invalid content_type. Must be track, zip, or subscription", 400);
    }

    // Fetch content details and calculate amount
    let amount = 0;
    let currency = "INR";
    let description = "";

    if (content_type === "track") {
      const { data: track, error } = await supabaseServer
        .from("tracks")
        .select("title, price")
        .eq("id", content_id)
        .single();

      if (error || !track) {
        return fail("Track not found", 404);
      }

      amount = track.price * 100; // Convert to paise
      description = `Track: ${track.title}`;

    } else if (content_type === "zip") {
      const { data: album, error } = await supabaseServer
        .from("album_packs")
        .select("title, price")
        .eq("id", content_id)
        .single();

      if (error || !album) {
        return fail("Album pack not found", 404);
      }

      amount = album.price * 100;
      description = `Album Pack: ${album.title}`;

    } else if (content_type === "subscription") {
      if (!plan || !["basic", "pro", "super"].includes(plan)) {
        return fail("Valid plan required for subscription (basic/pro/super)", 400);
      }

      // Get subscription pricing from system_settings
      const { data: settings } = await supabaseServer
        .from("system_settings")
        .select("value")
        .eq("key", "minimum_pricing")
        .single();

      const pricing = settings?.value as any;
      const planKey = `subscription_${plan}`;
      
      if (!pricing || !pricing[planKey]) {
        return fail("Subscription pricing not configured", 500);
      }

      amount = pricing[planKey] * 100;
      
      // Get DJ name for description
      const { data: dj } = await supabaseServer
        .from("dj_profiles")
        .select("dj_name")
        .eq("id", content_id)
        .single();

      description = `${plan.toUpperCase()} Subscription - ${dj?.dj_name || "DJ"}`;
    }

    // Get payment provider
    const paymentProvider = await getPaymentProvider();

    // Create order
    const receipt = `${content_type}_${content_id}_${Date.now()}`;
    
    const order = await paymentProvider.createOrder({
      amount,
      currency,
      receipt,
      notes: {
        user_id: user.id,
        content_type,
        content_id,
        plan: plan || "",
      },
    });

    console.log(`[PAYMENT_ORDER_CREATED] User: ${user.email} | ${description} | ₹${amount / 100}`);

    return ok({
      orderId: order.orderId,
      amount: order.amount,
      currency: order.currency,
      keyId: order.keyId, // For Razorpay frontend
      checkoutUrl: order.checkoutUrl, // For PhonePe redirect
      description,
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    console.error("[PAYMENT_CREATE_ERROR]", err);
    return fail(err.message || "Failed to create payment order", 500);
  }
}
