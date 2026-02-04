import { supabaseServer } from "@/app/lib/supabaseServer";
import { logger } from "@/app/lib/logger";
import { ok, fail } from "@/app/lib/apiResponse";

/**
 * GET /api/cron/cleanup
 * 
 * Performs house-keeping on the database:
 * 1. Deletes expired rate limit records.
 * 2. Deletes expired download tokens.
 */
export async function GET(req: Request) {
    const { searchParams } = new URL(req.url);
    const secret = searchParams.get("secret");

    if (secret !== process.env.CRON_SECRET) {
        return fail("Unauthorized", 401, "CRON");
    }

    try {
        const now = new Date().toISOString();

        // 1. Cleanup rate limits
        const { error: rlError, count: rlCount } = await supabaseServer
            .from("rate_limits")
            .delete({ count: "exact" })
            .lt("reset_at", now);

        if (rlError) logger.error("CRON", "Rate limit cleanup failed", rlError);

        // 2. Cleanup expired download tokens (older than 24h of expiry to be safe)
        const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
        const { error: tokenError, count: tokenCount } = await supabaseServer
            .from("download_tokens")
            .delete({ count: "exact" })
            .lt("expires_at", dayAgo);

        if (tokenError) logger.error("CRON", "Token cleanup failed", tokenError);

        logger.info("CRON", "Cleanup complete", {
            clearedRateLimits: rlCount,
            clearedTokens: tokenCount
        });

        return ok({
            success: true,
            clearedRateLimits: rlCount,
            clearedTokens: tokenCount
        });

    } catch (err) {
        logger.error("CRON", "Cleanup cron failed", err);
        return fail("Cleanup failed", 500, "CRON");
    }
}
