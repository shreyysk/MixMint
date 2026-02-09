import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { trackReferral, awardSignupBonus } from "@/lib/rewards";

export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const { referralCode } = await req.json();
    
    // Check if referral already tracked for this user
    const { data: existingReferral } = await supabaseServer
      .from('referrals')
      .select('id')
      .eq('referred_id', user.id)
      .single();

    if (existingReferral) {
        // Just ensure signup bonus is awarded if not already
        await awardSignupBonus(user.id);
        return ok({ success: true, message: "Referral already tracked" });
    }

    // This will award signup bonus AND track referral if code is provided
    await trackReferral(user.id, referralCode || null);
    
    return ok({ success: true });
  } catch (err: any) {
    console.error("[TRACK_SIGNUP_API_ERROR]:", err);
    return fail(err.message || "Internal error", 500);
  }
}
