
import { supabaseServer } from "./supabaseServer";

/**
 * awardPoints
 * Atomically increments a user's points balance and records a history entry.
 */
export async function awardPoints(userId: string, amount: number, type: string, description: string) {
    if (amount <= 0) return;

    try {
        // 1. Increment Balance
        const { error: updateError } = await supabaseServer.rpc('increment_points_balance', {
            target_id: userId,
            amount: Math.floor(amount)
        });

        if (updateError) throw updateError;

        // 2. Record History
        const { error: historyError } = await supabaseServer
            .from('points_history')
            .insert({
                profile_id: userId,
                amount: Math.floor(amount),
                type,
                description
            });

        if (historyError) {
            console.error("[AWARD_POINTS_HISTORY_ERROR]:", historyError);
            // We don't fail the whole process if history fails, but we log it.
        }

    } catch (err) {
        console.error("[AWARD_POINTS_ERROR]:", err);
    }
}

/**
 * handlePurchasePoints
 * Standard handler for awarding points on purchase (1% rate).
 */
export async function handlePurchasePoints(userId: string, amountPaid: number) {
    const pointsAmount = Math.floor(amountPaid); // 1 point per ₹100 is too low? Let's do 1 point per ₹1 (1%)
    // Wait, amountPaid is in INR. 1% of ₹1000 is 10 points. 
    // 1% rate = amountPaid / 1? No, amountPaid * 0.01.
    // Let's do 1 point per ₹10 spent (standard).
    const points = Math.floor(amountPaid / 10);
    
    if (points > 0) {
        await awardPoints(
            userId, 
            points, 
            'purchase_reward', 
            `Points earned for purchase of ₹${amountPaid}`
        );
    }
}

/**
 * generateReferralCode
 * Generates and saves a unique referral code for a user.
 */
export async function generateReferralCode(userId: string) {
    const code = `MIX-${userId.slice(0, 4)}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    
    await supabaseServer
        .from('profiles')
        .update({ referral_code: code })
        .eq('id', userId);
    
    return code;
}

/**
 * awardSignupBonus
 * Awards a one-time bonus for joining.
 */
export async function awardSignupBonus(userId: string) {
    // Check if already awarded
    const { data: existing } = await supabaseServer
        .from('points_history')
        .select('id')
        .eq('profile_id', userId)
        .eq('type', 'signup_bonus')
        .single();
    
    if (!existing) {
        await awardPoints(userId, 50, 'signup_bonus', 'Welcome to MixMint!');
    }
}

/**
 * awardEngagementPoints
 * Simple bonus for engagement (follows, reviews).
 */
export async function awardEngagementPoints(userId: string, targetId: string, type: 'follow' | 'review') {
    // Check for idempotency (e.g. only award follow bonus once per DJ)
    const { data: existing } = await supabaseServer
        .from('points_history')
        .select('id')
        .eq('profile_id', userId)
        .eq('type', `${type}_reward`)
        .ilike('description', `%${targetId.slice(0, 8)}%`)
        .single();

    if (!existing) {
        const points = type === 'follow' ? 10 : 25;
        const desc = type === 'follow' ? `Followed DJ ${targetId.slice(0, 8)}...` : `Reviewed item ${targetId.slice(0, 8)}...`;
        await awardPoints(userId, points, `${type}_reward`, desc);
    }
}

/**
 * trackReferral
 * Records a referral relationship.
 */
export async function trackReferral(referredId: string, referralCode: string | null) {
    // 1. Award Signup Bonus
    await awardSignupBonus(referredId);

    if (!referralCode) return;

    // 2. Resolve Referrer from profiles
    const { data: referrerProfile } = await supabaseServer
        .from('profiles')
        .select('id')
        .eq('referral_code', referralCode)
        .single();
    
    if (referrerProfile && referrerProfile.id !== referredId) {
        // Link them in referrals table
        await supabaseServer.from('referrals').insert({
            referrer_id: referrerProfile.id,
            referred_id: referredId,
            referral_code: referralCode,
            status: 'pending'
        });
    }

}

/**
 * redeemPoints
 * Deducts points from user balance.
 */
export async function redeemPoints(userId: string, amount: number, description: string) {
    if (amount <= 0) return;

    try {
        // 1. Decrement Balance (using negative increment)
        const { error: updateError } = await supabaseServer.rpc('increment_points_balance', {
            target_id: userId,
            amount: -Math.floor(amount)
        });

        if (updateError) throw updateError;

        // 2. Record History
        await supabaseServer
            .from('points_history')
            .insert({
                profile_id: userId,
                amount: -Math.floor(amount), // Negative amount for history
                type: 'redemption',
                description
            });

    } catch (err) {
        console.error("[REDEEM_POINTS_ERROR]:", err);
        throw err;
    }
}

/**
 * checkReferralMilestones
 * Checks if the seller was referred and awards bonuses to the referrer based on sales milestones.
 */
export async function checkReferralMilestones(sellerId: string) {
    try {
        // 1. Check if seller was referred
        const { data: referral } = await supabaseServer
            .from('referrals')
            .select('referrer_id')
            .eq('referred_id', sellerId)
            .single();

        if (!referral) return;

        // 2. Count total sales by this seller
        const { count, error } = await supabaseServer
            .from('purchases')
            .select('id', { count: 'exact', head: true })
            .eq('seller_id', sellerId);

        if (error || count === null) return;

        // 3. Define Milestones
        const milestones = [
            { count: 1, points: 100, desc: "Referral Bonus: DJ's First Sale" },
            { count: 10, points: 500, desc: "Referral Bonus: DJ's 10th Sale" },
            { count: 50, points: 2500, desc: "Referral Bonus: DJ's 50th Sale" }
        ];

        // 4. Check matching milestone
        const milestone = milestones.find(m => m.count === count);

        if (milestone) {
            // 5. Check if already awarded (idempotency)
            const uniqueKey = `referral_milestone_${sellerId}_${milestone.count}`;
            
            const { data: existing } = await supabaseServer
                .from('points_history')
                .select('id')
                .eq('profile_id', referral.referrer_id)
                .ilike('description', `%DJ's ${milestone.count}th Sale%`) 
                .single();

            if (!existing) {
                await awardPoints(
                    referral.referrer_id,
                    milestone.points,
                    'referral_milestone',
                    `${milestone.desc} (DJ: ${sellerId.slice(0,8)}...)`
                );
            }
        }

    } catch (err) {
        console.error("[REFERRAL_MILESTONE_ERROR]", err);
    }
}
