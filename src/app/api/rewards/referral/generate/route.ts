
import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

export async function POST() {
    try {
        const user = await requireAuth();

        // 1. Check if user already has a code
        const { data: existing } = await supabaseServer
            .from('referrals')
            .select('referral_code')
            .eq('referrer_id', user.id)
            .limit(1)
            .maybeSingle();

        // 2. Generate new code (simple alphanumeric)
        const newCode = `MIX-${user.id.slice(0, 4)}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

        // 3. Save to profile
        await supabaseServer
            .from('profiles')
            .update({ referral_code: newCode })
            .eq('id', user.id);

        return ok({ referralCode: newCode });
    } catch (err: any) {
        return fail(err.message, 500);
    }
}
