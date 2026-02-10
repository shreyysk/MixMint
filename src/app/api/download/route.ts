import { getClientIp, checkRateLimit } from "@/lib/rateLimit";
import { fail } from "@/lib/apiResponse";
import { DownloadService } from "@/server/services/DownloadService";
import { isVpnOrProxy } from "@/lib/security/vpn";

/**
 * GET /api/download
 * Exposes a temporary, IP-locked download stream for a valid token.
 */
export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const token = searchParams.get("token");

    if (!token) return fail("Token is required", 400);

    const clientIp = getClientIp(req);
    const userAgent = req.headers.get("user-agent") || "unknown";

    // 1. VPN Detection (Anti-Piracy Phase)
    const isVpn = await isVpnOrProxy(clientIp);
    if (isVpn) {
        return fail("Downloads via VPN or Proxy are not allowed for security reasons.", 403);
    }

    // 2. Global Rate Limiting per IP
    const rl = await checkRateLimit("download_start", clientIp, 20, 3600); 
    if (!rl.success) {
        return fail("Download limit reached. Please try again in an hour.", 429);
    }

    // 3. Validate Token & Get Content Context
    const { tokenRow, content } = await DownloadService.validateToken(token, clientIp);

    // 4. Concurrent Download Limit (Lock down account sharing)
    await DownloadService.checkConcurrentLimit(tokenRow.user_id, 3);

    // 6. Get File Stream
    const { Body, ContentType, ContentLength } = await DownloadService.getFileStream(content.file_key);

    // 7. Return Stream Response
    const responseHeaders = new Headers();
    responseHeaders.set("Content-Type", ContentType || "application/octet-stream");
    if (ContentLength) responseHeaders.set("Content-Length", ContentLength.toString());
    
    // Suggest filename for the browser
    const extension = content.file_key.split('.').pop() || (tokenRow.content_type === "track" ? "mp3" : "zip");
    responseHeaders.set(
      "Content-Disposition", 
      `attachment; filename="${content.title.replace(/[^a-zA-Z0-9]/g, '_')}.${extension}"`
    );

    return new Response(Body as any, {
      status: 200,
      headers: responseHeaders,
    });

  } catch (err: any) {
    console.error("[DOWNLOAD_PROXY_ERROR]:", err);
    return fail(err.message || "Internal server error during download proxy.", 500);
  }
}
