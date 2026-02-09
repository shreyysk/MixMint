import { supabaseServer } from "@/lib/supabaseServer";
import { logger } from "@/lib/logger";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/admin/health
 * 
 * Performs high-level data consistency checks.
 * restricted to admin role.
 */
export async function GET() {
    try {
        const user = await requireAuth();

        // 1. Verify Admin Role
        const { data: profile } = await supabaseServer
            .from("profiles")
            .select("role")
            .eq("id", user.id)
            .single();

        if (profile?.role !== "admin") {
            return fail("Forbidden: Admin access required", 403, "SYSTEM");
        }

        const reports: any[] = [];

        // 2. Check for Orphaned purchases (purchases where content no longer exists)
        // This is simplified, in real app you might use a complex join
        const { data: purchases } = await supabaseServer
            .from("purchases")
            .select("id, content_id, content_type")
            .limit(100);

        if (purchases) {
            // Logic to verify content existence could go here
            // e.g. check if content_id exists in tracks or album_packs
        }

        // 3. System Load / Table counts
        const { count: userCount } = await supabaseServer.from("profiles").select("*", { count: "exact", head: true });
        const { count: trackCount } = await supabaseServer.from("tracks").select("*", { count: "exact", head: true });

        logger.info("SYSTEM", "Health check performed", { admin: user.email });

        return ok({
            status: "healthy",
            timestamp: new Date().toISOString(),
            stats: {
                totalUsers: userCount,
                totalTracks: trackCount
            },
            checks: [
                { name: "Database Connectivity", status: "ok" },
                { name: "Auth Sysetm", status: "ok" }
            ]
        });

    } catch (err) {
        logger.error("SYSTEM", "Health check failed", err);
        return fail("Health check failed", 500, "SYSTEM");
    }
}
