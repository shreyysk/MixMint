import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * Calculates the revenue split between the DJ and the Platform.
 * Default is 80% to DJ, 20% to Platform.
 */
export async function calculateRevenueSplit(djId: string, totalAmount: number) {
    try {
        const { data: settings } = await supabaseServer
            .from("monetization_settings")
            .select("revenue_share_pct")
            .eq("dj_id", djId)
            .single();

        const djSharePct = settings?.revenue_share_pct || 80.00;
        const djAmount = (totalAmount * djSharePct) / 100;
        const platformAmount = totalAmount - djAmount;

        return {
            djAmount,
            platformAmount,
            djSharePct,
        };
    } catch (err) {
        logger.warn("SYSTEM", "Failed to fetch monetization settings, using defaults", { djId });
        const djAmount = (totalAmount * 80) / 100;
        return {
            djAmount,
            platformAmount: totalAmount - djAmount,
            djSharePct: 80,
        };
    }
}
