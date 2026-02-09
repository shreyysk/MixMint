import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * Lightweight, database-backed rate limiter for distributed serverless environments.
 * Uses a Fixed Window algorithm.
 */

interface RateLimitResult {
    success: boolean;
    limit: number;
    remaining: number;
    reset: number; // UTC Timestamp in seconds
}

export async function checkRateLimit(
    tag: string,
    identifier: string,
    limit: number,
    windowSeconds: number
): Promise<RateLimitResult> {
    const key = `rl:${tag}:${identifier}`;
    const now = new Date();

    try {
        // 1. Get current limit record
        const { data: record, error } = await supabaseServer
            .from("rate_limits")
            .select("count, reset_at")
            .eq("key", key)
            .single();

        if (error && error.code !== "PGRST116") { // PGRST116 is 'no rows returned'
            logger.error("SYSTEM", "Rate limit check failed", error, { key });
            return { success: true, limit, remaining: limit - 1, reset: Math.floor(now.getTime() / 1000) + windowSeconds };
        }

        const resetAt = record ? new Date(record.reset_at) : null;
        const isExpired = !resetAt || now > resetAt;

        if (isExpired) {
            // Create or reset the window
            const newResetAt = new Date(now.getTime() + windowSeconds * 1000);

            const { error: upsertError } = await supabaseServer
                .from("rate_limits")
                .upsert({
                    key,
                    count: 1,
                    reset_at: newResetAt.toISOString()
                }, { onConflict: 'key' });

            if (upsertError) {
                logger.error("SYSTEM", "Rate limit upsert failed", upsertError, { key });
            }

            return {
                success: true,
                limit,
                remaining: limit - 1,
                reset: Math.floor(newResetAt.getTime() / 1000)
            };
        }

        // Window is active, check count
        if (!record || record.count >= limit) {
            logger.warn("SYSTEM", "Rate limit exceeded", { key, count: record?.count, limit });
            return {
                success: false,
                limit,
                remaining: 0,
                reset: resetAt ? Math.floor(resetAt.getTime() / 1000) : Math.floor(now.getTime() / 1000)
            };
        }

        // Increment count
        const { error: incError } = await supabaseServer
            .from("rate_limits")
            .update({ count: record.count + 1 })
            .eq("key", key);

        if (incError) {
            logger.error("SYSTEM", "Rate limit increment failed", incError, { key });
        }

        return {
            success: true,
            limit,
            remaining: limit - (record.count + 1),
            reset: Math.floor(resetAt.getTime() / 1000)
        };

    } catch (err) {
        logger.error("SYSTEM", "Rate limit catastrophic failure", err, { key });
        // Fail-open strategy: allow request if rate limiter is down to avoid blocking users
        return { success: true, limit, remaining: 1, reset: Math.floor(now.getTime() / 1000) + 60 };
    }
}

/**
 * Helper to get client IP from request headers
 */
export function getClientIp(req: Request): string {
    return req.headers.get("x-forwarded-for")?.split(",")[0] ||
        req.headers.get("x-real-ip") ||
        "127.0.0.1";
}
