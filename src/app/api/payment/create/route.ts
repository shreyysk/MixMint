
import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/requireAuth";
import { supabaseServer } from "@/lib/supabaseServer";
import { getPaymentProvider } from "@/lib/payments";
import { ok, fail } from "@/lib/apiResponse";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const body = await req.json();

    const { content_type, content_id, plan, points_to_redeem } = body;

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
      // 1. Check if already purchased
      const { data: existing } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", user.id)
        .eq("content_id", content_id)
        .eq("content_type", "track")
        .single();

      if (existing) {
        return fail("You already own this track", 400);
      }

      const { data: track, error } = await supabaseServer
        .from("tracks")
        .select("title, price")
        .eq("id", content_id)
        .single();

      if (error || !track) {
        return fail("Track not found", 404);
      }

      if (track.price > 0 && track.price < 29) {
          return fail("Price is below platform minimum (₹29)", 400);
      }

      amount = track.price * 100; // Convert to paise
      description = `Track: ${track.title}`;

    } else if (content_type === "zip") {
      // 1. Check if already purchased
      const { data: existing } = await supabaseServer
        .from("purchases")
        .select("id")
        .eq("user_id", user.id)
        .eq("content_id", content_id)
        .eq("content_type", "zip")
        .single();

      if (existing) {
        return fail("You already own this album pack", 400);
      }

      const { data: album, error } = await supabaseServer
        .from("album_packs")
        .select("title, price")
        .eq("id", content_id)
        .single();

      if (error || !album) {
        return fail("Album pack not found", 404);
      }

      if (album.price < 79) {
          return fail("Price is below platform minimum (₹79)", 400);
      }

      amount = album.price * 100;
      description = `Album Pack: ${album.title}`;

    } else if (content_type === "subscription") {
      if (!plan || !["basic", "pro", "super"].includes(plan)) {
        return fail("Valid plan required for subscription (basic/pro/super)", 400);
      }

      // Check if active subscription already exists
      const { data: existingSub } = await supabaseServer
        .from("dj_subscriptions")
        .select("expires_at")
        .eq("user_id", user.id)
        .eq("dj_id", content_id)
        .gt("expires_at", new Date().toISOString())
        .single();

      // We allow purchase if it expires within 7 days, otherwise block to prevent overkill
      if (existingSub) {
          const expires = new Date(existingSub.expires_at);
          const now = new Date();
          const diffDays = Math.ceil((expires.getTime() - now.getTime()) / (1000 * 3600 * 24));
          if (diffDays > 7) {
              return fail(`You have an active subscription for another ${diffDays} days.`, 400);
          }
      }

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

    // Points Redemption
    let discount = 0;
    if (points_to_redeem > 0) {
      const { data: pointsData, error: pointsError } = await supabaseServer
        .from('points')
        .select('balance')
        .eq('user_id', user.id)
        .single();

      if (pointsError || !pointsData) {
        return fail("Could not retrieve user points balance.", 500);
      }

      if (pointsData.balance < points_to_redeem) {
        return fail("Not enough points to redeem.", 400);
      }

      const maxRedeemable = Math.floor(amount * 0.2); // 20% cap
      const pointsToUse = Math.min(points_to_redeem, maxRedeemable);
      discount = pointsToUse;
      amount -= discount;
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
        points_used: String(discount),
      },
    });

    console.log(`[PAYMENT_ORDER_CREATED] User: ${user.email} | ${description} | ₹${amount / 100} (after ${discount} points discount)`);

    return ok({
      orderId: order.orderId,
      amount: order.amount,
      currency: order.currency,
      keyId: order.keyId, // For Razorpay frontend
      checkoutUrl: order.checkoutUrl, // For PhonePe redirect
      description,
      discount: discount || 0,
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    console.error("[PAYMENT_CREATE_ERROR]", err);
    return fail(err.message || "Failed to create payment order", 500);
  }
}
