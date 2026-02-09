import { supabaseServer } from "@/lib/supabaseServer";
import { logger } from "@/lib/logger";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/cron/sub-expiry
 * 
 * Logic to handle expired subscriptions if needed.
 * Currently, our system uses 'expires_at' in queries, but we might want 
 * to do cleanup or send notification hooks here.
 */
export async function GET(req: Request) {
    const { searchParams } = new URL(req.url);
    const secret = searchParams.get("secret");

    if (secret !== process.env.CRON_SECRET) {
        return fail("Unauthorized", 401, "CRON");
    }

    try {
        const now = new Date().toISOString();

        // Example: Find subscriptions that just expired in the last 24h and haven't been notified
        // For now, we will just log the count of expired subscriptions
        const { count, error } = await supabaseServer
            .from("dj_subscriptions")
            .select("*", { count: "exact", head: true })
            .lt("expires_at", now);

        if (error) throw error;

        logger.info("CRON", "Subscription expiry check complete", { expiredCount: count });

        return ok({
            success: true,
            message: `Checked subscriptions. ${count} currently expired.`,
            timestamp: now
        });

    } catch (err) {
        logger.error("CRON", "Subscription expiry cron failed", err);
        return fail("Cron execution failed", 500, "CRON");
    }
}
