import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";

export async function POST(req: Request) {
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
