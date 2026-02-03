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
}
