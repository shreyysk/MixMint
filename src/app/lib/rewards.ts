import { supabaseServer } from "./supabaseServer";

/**
 * Generate a unique referral code
 * Format: MIX-XXXXXX (6 alphanumeric chars)
 */
export async function generateReferralCode(profileId: string): Promise<string> {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // No similar looking chars (O/0, I/1)
    let code = '';

    // Check if user already has a code
    const { data: existingCode } = await supabaseServer
        .from('referral_codes')
        .select('code')
        .eq('profile_id', profileId)
        .single();

    if (existingCode) return existingCode.code;

    // Try generating codes until we find a unique one
    while (true) {
        code = 'MIX-';
        for (let i = 0; i < 6; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }

        const { data: existing } = await supabaseServer
            .from('referral_codes')
            .select('code')
            .eq('code', code)
            .single();

        if (!existing) break;
    }

    const { error } = await supabaseServer
        .from('referral_codes')
        .insert({ profile_id: profileId, code });

    if (error) {
        console.error("[GENERATE_REFERRAL_CODE_ERROR]:", error);
        throw error;
    }

    return code;
}

/**
 * Award points to a user and log history
 */
export async function awardPoints(
    profileId: string,
    points: number,
    eventType: string,
    metadata: any = {}
) {
    if (points === 0) return;

    try {
        // Get current balance
        const { data: currentBalance } = await supabaseServer
            .from('user_points')
            .select('balance, total_earned')
            .eq('profile_id', profileId)
            .single();

        if (currentBalance) {
            await supabaseServer
                .from('user_points')
                .update({
                    balance: currentBalance.balance + points,
                    total_earned: currentBalance.total_earned + (points > 0 ? points : 0),
                    updated_at: new Date().toISOString()
                })
                .eq('profile_id', profileId);
        } else {
            await supabaseServer
                .from('user_points')
                .insert({
                    profile_id: profileId,
                    balance: points,
                    total_earned: points > 0 ? points : 0
                });
        }

        // Log history
        await supabaseServer
            .from('points_history')
            .insert({
                profile_id: profileId,
                points,
                event_type: eventType,
                metadata
            });
    } catch (err) {
        console.error("[AWARD_POINTS_ERROR]:", err);
        // Don't throw, we don't want to break the main flow (e.g. signup) if points fail
    }
}

/**
 * Award points for a new user signup
 */
export async function awardSignupBonus(profileId: string) {
    try {
        // Check if already awarded
        const { data: existing } = await supabaseServer
            .from('points_history')
            .select('id')
            .eq('profile_id', profileId)
            .eq('event_type', 'signup_bonus')
            .single();

        if (existing) return;

        await awardPoints(profileId, 50, 'signup_bonus');
    } catch (err) {
        console.error("[SIGNUP_BONUS_ERROR]:", err);
    }
}

/**
 * Track a referral signup
 */
export async function trackReferral(referredId: string, referralCode: string) {
    try {
        // Always award signup bonus first
        await awardSignupBonus(referredId);

        if (!referralCode) return;

        // Find referrer
        const { data: codeData } = await supabaseServer
            .from('referral_codes')
            .select('profile_id')
            .eq('code', referralCode.toUpperCase())
            .single();

        if (!codeData || codeData.profile_id === referredId) return;

        // Record referral
        const { error } = await supabaseServer
            .from('referrals')
            .insert({
                referrer_id: codeData.profile_id,
                referred_id: referredId,
                status: 'joined'
            });

        if (error) {
            if (error.code === '23505') return; // Already referred
            throw error;
        }

        // Award a small bonus to the referrer for the signup
        await awardPoints(codeData.profile_id, 20, 'referral_signup', { referred_id: referredId });

    } catch (err) {
        console.error("[TRACK_REFERRAL_ERROR]:", err);
    }
}

/**
 * Handle points for successful purchase and verify referral conversions
 */
export async function handlePurchasePoints(userId: string, amount: number) {
    try {
        const points = Math.floor(amount / 10);
        if (points > 0) {
            await awardPoints(userId, points, 'purchase', { amount });
        }

        // Check if user was referred and this is their first purchase
        // A referral status of 'joined' means they haven't made a verified purchase yet
        const { data: referral } = await supabaseServer
            .from('referrals')
            .select('id, referrer_id, status')
            .eq('referred_id', userId)
            .eq('status', 'joined')
            .single();

        if (referral) {
            // First purchase! Upgrade referral status to 'verified'
            await supabaseServer
                .from('referrals')
                .update({ status: 'verified', points_awarded: true })
                .eq('id', referral.id);

            // Award conversion bonus to referrer (100 points)
            await awardPoints(referral.referrer_id, 100, 'referral_conversion', { referred_id: userId });

            console.log(`[REFERRAL_VERIFIED] Referrer: ${referral.referrer_id} | Referred: ${userId}`);
        }
    } catch (err) {
        console.error("[HANDLE_PURCHASE_POINTS_ERROR]:", err);
    }
}
