import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * MixMint Referral Tier Logic
 * Bronze: 0-5 referrals (Standard comisión)
 * Silver: 6-20 referrals (Reduced platform fee)
 * Gold: 21-100 referrals (Premium support + lower fee)
 * Platinum: 100+ referrals (VIP access)
 */

export type ReferralTier = 'bronze' | 'silver' | 'gold' | 'platinum';

const TIER_THRESHOLDS = {
    bronze: 0,
    silver: 5,
    gold: 20,
    platinum: 100
};

/**
 * checkAndPromoteReferralTier
 * Checks if a DJ is eligible for a tier upgrade based on verified referrals.
 */
export async function checkAndPromoteReferralTier(djId: string) {
    try {
        // 1. Count verified referrals
        const { count, error } = await supabaseServer
            .from('referrals')
            .select('*', { count: 'exact', head: true })
            .eq('referrer_id', djId)
            .eq('status', 'verified');

        if (error || count === null) throw error;

        // 2. Identify new tier
        let newTier: ReferralTier = 'bronze';
        if (count >= TIER_THRESHOLDS.platinum) newTier = 'platinum';
        else if (count >= TIER_THRESHOLDS.gold) newTier = 'gold';
        else if (count >= TIER_THRESHOLDS.silver) newTier = 'silver';

        // 3. Get current tier
        const { data: profile } = await supabaseServer
            .from('profiles')
            .select('referral_tier')
            .eq('id', djId)
            .single();

        if (profile?.referral_tier !== newTier) {
            // 4. Update Tier
            const { error: updateErr } = await supabaseServer
                .from('profiles')
                .update({ referral_tier: newTier })
                .eq('id', djId);

            if (updateErr) throw updateErr;

            logger.info("REWARDS", `DJ Tier Promoted`, { djId, oldTier: profile?.referral_tier, newTier });
            
            // Optional: Trigger notification to DJ
        }
        
        return newTier;

    } catch (err) {
        logger.error("REWARDS", "Failed to check referral tier promotion", err, { djId });
        return null;
    }
}
