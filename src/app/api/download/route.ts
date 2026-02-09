import { getClientIp } from "@/lib/rateLimit";
import { fail } from "@/lib/apiResponse";
import { DownloadService } from "@/server/services/DownloadService";

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

    // 1. Validate Token & Get Content Context
    const { tokenRow, content } = await DownloadService.validateToken(token, clientIp);

    // 2. Mark as Used & Handle Quota
    await DownloadService.markAsUsed(token, tokenRow);

    // 3. Get File Stream
    const { Body, ContentType, ContentLength } = await DownloadService.getFileStream(content.file_key);

    // 4. Return Stream Response
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
    return fail("Internal server error during download proxy.", 500);
  }
}
