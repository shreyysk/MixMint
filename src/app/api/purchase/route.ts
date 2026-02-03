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

  /* ORIGINAL CODE - DISABLED FOR SECURITY
  try {
    const user = await requireAuth();
    const body = await req.json();

    const { content_type, content_id, price } = body;

    if (!content_type || !content_id) {
      return NextResponse.json(
        { error: "Invalid purchase payload" },
        { status: 400 }
      );
    }

    // Prevent duplicate purchase
    const { data: existing } = await supabaseServer
      .from("purchases")
      .select("id")
      .eq("user_id", user.id)
      .eq("content_type", content_type)
      .eq("content_id", content_id)
      .single();

    if (existing) {
      return NextResponse.json(
        { error: "Already purchased" },
        { status: 409 }
      );
    }

    const { error } = await supabaseServer
      .from("purchases")
      .insert({
        user_id: user.id,
        content_type,
        content_id,
        price: price ?? 0,
      });

    if (error) {
      console.error("[PURCHASE_ERROR]", error);
      return NextResponse.json(
        { error: "Purchase failed" },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    console.error("[PURCHASE_FATAL]", err);
    return NextResponse.json(
      { error: "Server error" },
      { status: 500 }
    );
  }
}
