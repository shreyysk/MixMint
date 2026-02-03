import { NextResponse } from "next/server";
import { requireAuth } from "@/app/lib/requireAuth";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { getPaymentProvider } from "@/app/lib/payments";
import { sendPurchaseEmail, sendSubscriptionEmail } from "@/app/lib/email";
import { ok, fail } from "@/app/lib/apiResponse";
import { SUBSCRIPTION_PLANS } from "@/app/lib/subscriptionPlans";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const body = await req.json();

    const { orderId, paymentId, signature, content_type, content_id, plan } = body;

    if (!orderId || !paymentId || !signature) {
      return fail("orderId, paymentId, and signature are required", 400);
    }

    // Get payment provider
    const paymentProvider = await getPaymentProvider();

    // Verify payment signature
    const isValid = await paymentProvider.verifyPayment({
      orderId,
      paymentId,
      signature,
    });

    if (!isValid) {
      console.error(`[PAYMENT_VERIFICATION_FAILED] User: ${user.email} | Payment: ${paymentId}`);
      return fail("Payment verification failed. Invalid signature.", 403);
    }

    console.log(`[PAYMENT_VERIFIED] User: ${user.email} | Payment: ${paymentId}`);

    // Get payment status to confirm amount
    const paymentStatus = await paymentProvider.getPaymentStatus(paymentId);

    if (paymentStatus.status !== "success") {
      return fail("Payment not successful", 400);
    }

    const amountPaid = paymentStatus.amount / 100; // Convert paise to rupees

    // Process based on content type
    if (content_type === "track" || content_type === "zip") {
      // Create purchase record
      const { error: purchaseError } = await supabaseServer
        .from("purchases")
        .insert({
          user_id: user.id,
          content_type,
          content_id,
          price: amountPaid,
          payment_id: paymentId,
          payment_order_id: orderId,
        });

      if (purchaseError) {
        console.error("[PURCHASE_INSERT_ERROR]", purchaseError);
        return fail("Failed to record purchase", 500);
      }

      // Send email (non-blocking)
      try {
        const contentTable = content_type === "track" ? "tracks" : "album_packs";
        const { data: content } = await supabaseServer
          .from(contentTable)
          .select("title")
          .eq("id", content_id)
          .single();

        const { data: profile } = await supabaseServer
          .from("profiles")
          .select("full_name")
          .eq("id", user.id)
          .single();

        if (content && profile && user.email) {
          // Generate download token
          const tokenRes = await fetch(`${process.env.NEXT_PUBLIC_APP_URL}/api/download-token`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${paymentId}`, // Temporary auth
            },
            body: JSON.stringify({ content_id, content_type }),
          });

          const tokenData = await tokenRes.json();
          const downloadUrl = `${process.env.NEXT_PUBLIC_APP_URL}/api/download?token=${tokenData.token}`;

          await sendPurchaseEmail({
            to: user.email,
            userName: profile.full_name,
            contentTitle: content.title,
            contentType: content_type,
            price: amountPaid,
            downloadUrl,
          });
        }
      } catch (emailError) {
        console.error("[EMAIL_ERROR]", emailError);
        // Don't fail the purchase if email fails
      }

      console.log(`[PURCHASE_COMPLETE] User: ${user.email} | ${content_type}: ${content_id} | ₹${amountPaid}`);

      return ok({
        success: true,
        message: "Purchase successful",
        content_type,
        content_id,
      });

    } else if (content_type === "subscription") {
      if (!plan) {
        return fail("Plan required for subscription", 400);
      }

      const planConfig = SUBSCRIPTION_PLANS[plan as keyof typeof SUBSCRIPTION_PLANS];
      if (!planConfig) {
        return fail("Invalid plan", 400);
      }

      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + planConfig.duration_days);

      // Create subscription record
      const { error: subError } = await supabaseServer
        .from("dj_subscriptions")
        .insert({
          user_id: user.id,
          dj_id: content_id,
          plan,
          track_quota: planConfig.track_quota,
          zip_quota: planConfig.zip_quota,
          fan_upload_quota: planConfig.fan_upload_quota,
          expires_at: expiresAt.toISOString(),
          payment_id: paymentId,
          payment_order_id: orderId,
        });

      if (subError) {
        console.error("[SUBSCRIPTION_INSERT_ERROR]", subError);
        return fail("Failed to create subscription", 500);
      }

      // Send email (non-blocking)
      try {
        const { data: dj } = await supabaseServer
          .from("dj_profiles")
          .select("dj_name")
          .eq("id", content_id)
          .single();

        const { data: profile } = await supabaseServer
          .from("profiles")
          .select("full_name")
          .eq("id", user.id)
          .single();

        if (dj && profile && user.email) {
          await sendSubscriptionEmail({
            to: user.email,
            userName: profile.full_name,
            djName: dj.dj_name,
            plan,
            trackQuota: planConfig.track_quota,
            zipQuota: planConfig.zip_quota,
            expiresAt: expiresAt.toISOString(),
          });
        }
      } catch (emailError) {
        console.error("[EMAIL_ERROR]", emailError);
      }

      console.log(`[SUBSCRIPTION_COMPLETE] User: ${user.email} | DJ: ${content_id} | Plan: ${plan} | ₹${amountPaid}`);

      return ok({
        success: true,
        message: "Subscription activated",
        plan,
        expires_at: expiresAt.toISOString(),
      });
    }

    return fail("Invalid content_type", 400);

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401);
    }
    console.error("[PAYMENT_VERIFY_ERROR]", err);
    return fail(err.message || "Payment verification failed", 500);
  }
}
