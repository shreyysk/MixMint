import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";

/**
 * @deprecated This API is deprecated and should not be used directly.
 * 
 * SECURITY WARNING: This endpoint creates purchases WITHOUT payment verification.
 * 
 * New purchase flow:
 * 1. POST /api/payment/create (create order)
 * 2. Complete payment via Razorpay/PhonePe
 * 3. POST /api/payment/verify (verify & create purchase)
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
        step1: "POST /api/payment/create",
        step2: "Complete payment",
        step3: "POST /api/payment/verify"
      }
    },
    { status: 410 } // Gone
  );
}
