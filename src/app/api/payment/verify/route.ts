import { NextResponse } from "next/server";
import { requireAuth } from "@/lib/requireAuth";
import { supabaseServer } from "@/lib/supabaseServer";
import { getPaymentProvider } from "@/lib/payments";
import { sendPurchaseEmail, sendSubscriptionEmail } from "@/lib/email";
import { ok, fail } from "@/lib/apiResponse";
import { SUBSCRIPTION_PLANS } from "@/lib/subscriptionPlans";
import { handlePurchasePoints, redeemPoints, checkReferralMilestones } from "@/lib/rewards";
import { logger } from "@/lib/logger";
import { checkRateLimit, getClientIp } from "@/lib/rateLimit";
import { calculateRevenueSplit, recordRevenue } from "@/lib/monetization";
import { DownloadService } from "@/server/services/DownloadService";

export async function POST(req: Request) {
  let user: any = null;
  try {
    user = await requireAuth();
    const body = await req.json();

    // --- RATE LIMITING ---
    const ip = getClientIp(req);
    const rl = await checkRateLimit("payment_verify", ip, 15, 3600); // 15 attempts per hour
    if (!rl.success) {
      logger.alert("PAYMENT", "ATTACK_WARNING: High frequency payment verification from single IP", { ip });
      return fail("Too many payment verification attempts. Please wait an hour.", 429, "PAYMENT");
    }

    const { orderId, paymentId, signature, content_type, content_id, plan, points_used } = body;

    if (!orderId || !paymentId || !signature) {
      return fail("orderId, paymentId, and signature are required", 400, "PAYMENT");
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
      logger.error("PAYMENT", "Payment verification failed", { user: user.email, paymentId });
      return fail("Payment verification failed. Invalid signature.", 403, "PAYMENT");
    }

    logger.info("PAYMENT", "Payment verified", { user: user.email, paymentId });

    // Get payment status to confirm amount
    const paymentStatus = await paymentProvider.getPaymentStatus(paymentId);

    if (paymentStatus.status !== "success") {
      return fail("Payment not successful", 400, "PAYMENT");
    }

    const amountPaid = paymentStatus.amount / 100; // Convert paise to rupees

    // Process based on content type
    if (content_type === "track" || content_type === "zip") {
      // Get DJ ID for split
      const contentTable = content_type === "track" ? "tracks" : "album_packs";
      const { data: item } = await supabaseServer
        .from(contentTable)
        .select("dj_id")
        .eq("id", content_id)
        .single();

      const purchaseDjId = item?.dj_id;
      if (purchaseDjId) {
        await recordRevenue(
          purchaseDjId, 
          amountPaid, 
          content_type === "track" ? "track_sale" : "zip_sale", 
          paymentId
        );
      }

      const clientIp = getClientIp(req);
      const userAgent = req.headers.get("user-agent") || "unknown";
      const country = req.headers.get("x-vercel-ip-country") || "unknown";
      const city = req.headers.get("x-vercel-ip-city") || "unknown";

      // Create purchase record with analytics
      const { error: purchaseError } = await supabaseServer
        .from("purchases")
        .insert({
          user_id: user.id,
          content_type,
          content_id,
          price: amountPaid,
          payment_id: paymentId,
          payment_order_id: orderId,
          seller_id: purchaseDjId,
          ip_address: clientIp,
          user_agent: userAgent,
          location_data: { country, city }
        });


      if (purchaseError) {
        logger.error("PAYMENT", "Purchase record failed", purchaseError, { user: user.id, paymentId });
        return fail("Failed to record purchase", 500, "PAYMENT");
      }

      // Check for DJ referral milestones (non-blocking)
      if (purchaseDjId) {
          checkReferralMilestones(purchaseDjId);
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
          const clientIp = getClientIp(req);
          const userAgent = req.headers.get("user-agent") || "unknown";

          // Generate Secure Token via Service directly (REFACTORED: NO INTERNAL FETCH)
          const tokenData = await DownloadService.generateToken(
            user.id,
            content_id, 
            content_type, 
            "purchase", 
            clientIp,
            userAgent
          );

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
        logger.error("PAYMENT", "Post-purchase email failed", emailError, { user: user.email });
        // Don't fail the purchase if email fails
      }

      logger.info("PAYMENT", "Purchase complete", { user: user.email, content_id, amountPaid });

      // Award points and handle referrals (non-blocking)
      handlePurchasePoints(user.id, amountPaid);

      // Deduct redeemed points
      if (points_used && points_used > 0) {
          await redeemPoints(user.id, points_used, `Redeemed for ${content_type} ${content_id}`);
      }

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
        return fail("Invalid plan", 400, "PAYMENT");
      }

      // Monetization split check
      await recordRevenue(content_id, amountPaid, "subscription", paymentId);

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
        logger.error("PAYMENT", "Subscription record failed", subError, { user: user.id, paymentId });
        return fail("Failed to create subscription", 500, "PAYMENT");
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

      logger.info("PAYMENT", "Subscription complete", { user: user.email, dj_id: content_id, plan, amountPaid });

      // Award points and handle referrals (non-blocking)
      handlePurchasePoints(user.id, amountPaid);

      // Deduct redeemed points
      if (points_used && points_used > 0) {
          await redeemPoints(user.id, points_used, `Redeemed for subscription ${plan} to ${content_id}`);
      }

      return ok({
        success: true,
        message: "Subscription activated",
        plan,
        expires_at: expiresAt.toISOString(),
      });
    }

    return fail("Invalid content_type", 400, "PAYMENT");

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return fail("Unauthorized", 401, "PAYMENT");
    }

    // CRITICAL ALERT: Log this so developers know immediately
    logger.alert("PAYMENT", "CRITICAL: Payment verification failed catastrophically", {
      error: err.message,
      user: user?.email,
      paymentId: req.headers.get("x-razorpay-payment-id") || "unknown"
    });

    return fail(err.message || "Payment verification failed", 500, "PAYMENT");
  }
}
