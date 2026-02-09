import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";
import { generateReferralCode } from "@/lib/rewards";

export async function GET() {
    try {
        const user = await requireAuth();

        // Get referral code
        const { data: profile } = await supabaseServer
            .from('profiles')
            .select('referral_code')
            .eq('id', user.id)
            .single();

        let code = profile?.referral_code;

        if (!code) {
            code = await generateReferralCode(user.id);
        }

        // Get stats
        const { data: referrals } = await supabaseServer
            .from('referrals')
            .select('status')
            .eq('referrer_id', user.id);

        const totalInvites = referrals?.length || 0;
        const successfulReferrals = referrals?.filter(r => r.status === 'verified').length || 0;

        return ok({
            code,
            stats: {
                totalInvites,
                successfulReferrals
            },
            link: `${process.env.NEXT_PUBLIC_APP_URL || 'https://mixmint.com'}/?ref=${code}`
        });
    } catch (err: any) {
        console.error("[REFERRAL_API_ERROR]:", err);
        return fail(err.message || "Internal error", 500);
    }
}
