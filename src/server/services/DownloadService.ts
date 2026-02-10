
import { supabaseAdmin } from "@/lib/supabaseServer";
import { r2 } from "@/lib/r2";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import crypto from "crypto";

export class DownloadService {
  /**
   * Check if user has exceeded concurrent download limit
   */
  static async checkConcurrentLimit(userId: string, limit: number = 3) {
    const { count, error } = await supabaseAdmin
      .from("download_tokens")
      .select("*", { count: "exact", head: true })
      .eq("user_id", userId)
      .eq("is_used", false)
      .gt("expires_at", new Date().toISOString());

    if (error) {
      console.error("[CONCURRENT_LIMIT_CHECK_ERROR]:", error);
      // Fail open if check fails to avoid blocking legitimate users
      return; 
    }

    if (count !== null && count >= limit) {
      // Log suspicious activity before throwing
      const { data: userDetails } = await supabaseAdmin.auth.admin.getUserById(userId);
      // We might not have IP/UA here easily unless passed down, but let's try to capture what we can
      // For now, trust the caller to handle the blocking.
      
      // Update: We should log this.
      // However, checkConcurrentLimit doesn't currently take IP/UA. 
      // We will rely on the route handler or update this signature in the next step if strictly needed.
      // ACTUALLY, let's update the signature to take metadata for better logging.
      
      throw new Error(`Download limit exceeded. You have ${count} active download links. Please use them or wait for them to expire (5 mins).`);
    }
  }

  /**
   * Check if user has exceeded concurrent download limit with logging
   */
  static async checkConcurrentLimitWithLogging(
      userId: string, 
      limit: number = 3,
      metadata: { ip: string, userAgent: string }
  ) {
     const { count, error } = await supabaseAdmin
      .from("download_tokens")
      .select("*", { count: "exact", head: true })
      .eq("user_id", userId)
      .eq("is_used", false)
      .gt("expires_at", new Date().toISOString());

    if (error) {
      console.error("[CONCURRENT_LIMIT_CHECK_ERROR]:", error);
      return; 
    }

    if (count !== null && count >= limit) {
        // Import dynamically to avoid circular deps if any (though none expected)
        const { SuspiciousActivityService } = await import("./SuspiciousActivityService");
        
        await SuspiciousActivityService.log("concurrent_download_limit_exceeded", {
            userId,
            ipAddress: metadata.ip,
            userAgent: metadata.userAgent,
            description: `User exceeded limit of ${limit} active downloads (Current: ${count})`
        });

        throw new Error(`Download limit exceeded. You have ${count} active download links.`);
    }
  }

  /**
   * Generate a secure, short-lived download token
   */
  static async generateToken(
    userId: string, 
    contentId: string, 
    contentType: string, 
    accessSource: string, 
    clientIp: string,
    userAgent: string,
    versionId?: string // Optional specific version
  ) {
    // 1. Generate Secure Token
    const token = crypto.randomBytes(32).toString("hex");
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 5); // 5 minute window

    // 2. Record Token in Database
    const { error: insertError } = await supabaseAdmin
      .from("download_tokens")
      .insert({
        token,
        user_id: userId,
        content_id: contentId,
        content_type: contentType,
        access_source: accessSource,
        expires_at: expiresAt.toISOString(),
        is_used: false,
        ip_address: clientIp,
        user_agent: userAgent,
        version_id: versionId
      });

    if (insertError) {
      console.error("[TOKEN_GEN_ERROR]:", insertError);
      throw new Error("Failed to generate download token");
    }

    return {
      token,
      expires_at: expiresAt.toISOString(),
    };
  }

  /**
   * Validate a download token and return content context
   * Hardened: Atomic "is_used" update to prevent race conditions (Replay Attacks)
   */
  static async validateToken(token: string, clientIp: string) {
    // 1. Validate Token & Atomic Mark-as-Used (PREVENT RACE CONDITION)
    // We update is_used = true ONLY if it was false and not expired.
    const { data: tokenResult, error: tokenError } = await supabaseAdmin
      .from("download_tokens")
      .update({ is_used: true })
      .eq("token", token)
      .eq("is_used", false)
      .gt("expires_at", new Date().toISOString())
      .select("*")
      .single();

    if (tokenError || !tokenResult) {
      throw new Error("Invalid, expired, or already used download token.");
    }

    const tokenRow = tokenResult;

    // 2. Strict IP Locking (MANDATORY)
    if (tokenRow.ip_address && tokenRow.ip_address !== clientIp) {
      throw new Error("Download link is locked to a different IP address.");
    }

    // 3. Content Retrieval Details
    const table = tokenRow.content_type === "track" ? "tracks" : "album_packs";
    
    // Fetch content info
    const { data: content, error: contentError } = await supabaseAdmin
      .from(table)
      .select("file_key, title, dj_id, expires_at")
      .eq("id", tokenRow.content_id)
      .single();

    if (contentError || !content) throw new Error("Content not found");

    if (content.expires_at && new Date(content.expires_at) < new Date()) {
        throw new Error("This content has expired and is no longer available.");
    }

    // 4. Check Access Revocation
    if (tokenRow.access_source === "purchase") {
        const { data: purchase } = await supabaseAdmin
            .from("purchases")
            .select("is_revoked")
            .eq("user_id", tokenRow.user_id)
            .eq("content_id", tokenRow.content_id)
            .single();
        
        if (purchase?.is_revoked) {
            throw new Error("Access has been revoked.");
        }
    }

    // 5. SECONDARY QUOTA CHECK (Anti-Bypass)
    // Verify subscription status/quota AGAIN at the moment of download.
    if (tokenRow.access_source === "subscription") {
        const { data: sub } = await supabaseAdmin
            .from("dj_subscriptions")
            .select("id, is_revoked, tracks_used, track_quota, zip_used, zip_quota, expires_at")
            .eq("user_id", tokenRow.user_id)
            .eq("dj_id", content.dj_id)
            .single();
        
        if (!sub || sub.is_revoked || new Date(sub.expires_at) < new Date()) {
            throw new Error("Active subscription required.");
        }

        // Strict limit check
        const used = tokenRow.content_type === "track" ? sub.tracks_used : sub.zip_used;
        const limit = tokenRow.content_type === "track" ? sub.track_quota : sub.zip_quota;

        if (used >= limit) {
            throw new Error("Subscription quota reached. Cannot fulfill download.");
        }

        // 6. Final Usage Increment
        const quotaField = tokenRow.content_type === "track" ? "tracks_used" : "zip_used";
        await supabaseAdmin.rpc('increment_subscription_usage', {
            sub_id: sub.id,
            field_name: quotaField
        });
    }

    // Handle specific version if requested
    if (tokenRow.version_id) {
        const { data: version } = await supabaseAdmin
            .from("track_versions")
            .select("file_key, format")
            .eq("id", tokenRow.version_id)
            .single();
            
        if (!version) throw new Error("Requested file version not found");
        
        return { tokenRow, content: { ...content, file_key: version.file_key, format: version.format } };
    }

    return { tokenRow, content };
  }


  /**
   * Get file stream from R2
   */
  static async getFileStream(fileKey: string) {
    const getCommand = new GetObjectCommand({
      Bucket: process.env.R2_BUCKET_NAME!,
      Key: fileKey,
    });

    try {
        const { Body, ContentType, ContentLength } = await r2.send(getCommand);
        if (!Body) throw new Error("Could not retrieve file body from storage.");
        return { Body, ContentType, ContentLength };
    } catch (err: any) {
        throw new Error("Failed to retrieve file from storage.");
    }
  }
}
