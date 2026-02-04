import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { ok, fail } from "@/app/lib/apiResponse";
import { generateReferralCode } from "@/app/lib/rewards";

export async function GET() {
    try {
        const user = await requireAuth();

        // Get referral code
        const { data: codeData } = await supabaseServer
            .from('referral_codes')
            .select('code')
            .eq('profile_id', user.id)
            .single();

        let code = codeData?.code;

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
            link: `${process.env.NEXT_PUBLIC_SITE_URL || 'https://mixmint.com'}/?ref=${code}`
        });
    } catch (err: any) {
        console.error("[REFERRAL_API_ERROR]:", err);
        return fail(err.message || "Internal error", 500);
    }
}
