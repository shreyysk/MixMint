import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { canAccessContent } from "@/lib/canAccessContent";
import { ok, fail } from "@/lib/apiResponse";
import { getClientIp } from "@/lib/rateLimit";
import { DownloadService } from "@/server/services/DownloadService";

/**
 * POST /api/download-token
 * Generates a short-lived (5 min), single-use token for content download.
 * Requires ownership (purchase) or active subscription quota.
 */
export async function POST(req: Request) {
  try {
    const user = await requireAuth();
    const clientIp = getClientIp(req);
    const body = await req.json();
    const { content_id, content_type, version_id } = body;

    if (!content_id || !content_type) {
      return fail("content_id and content_type are required", 400);
    }

    // 1. Check Access Permission
    // Note: We might want to verify version_id belongs to content_id, but validateToken will fail if not found.
    const access = await canAccessContent(user.id, content_type, content_id);

    if (!access.allowed) {
      return fail("Access denied. No active purchase or subscription quota.", 403);
    }

    // 2. Check Concurrent Download Limit (Anti-Piracy) with logging
    const userAgent = req.headers.get("user-agent") || "unknown";
    
    await DownloadService.checkConcurrentLimitWithLogging(user.id, 3, {
        ip: clientIp || "unknown",
        userAgent
    }); 

    // 3. Generate Secure Token via Service
    const result = await DownloadService.generateToken(
        user.id, 
        content_id, 
        content_type, 
        access.via || "unknown", 
        clientIp || "unknown",
        userAgent,
        version_id // Optional
    );

    return ok(result);

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    console.error("[DOWNLOAD_TOKEN_ROUTE_ERROR]:", err);
    return fail(err.message || "Internal server error", 500);
  }
}