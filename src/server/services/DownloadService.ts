
import { supabaseAdmin } from "@/lib/supabaseServer";
import { r2 } from "@/lib/r2";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import crypto from "crypto";

export class DownloadService {
  /**
   * Generate a secure, short-lived download token
   */
  static async generateToken(
    userId: string, 
    contentId: string, 
    contentType: string, 
    accessSource: string, 
    clientIp: string
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
        ip_address: clientIp
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
   */
  static async validateToken(token: string, clientIp: string) {
    // 1. Validate Token (Atomic check)
    const { data: tokenRow, error: tokenError } = await supabaseAdmin
      .from("download_tokens")
      .select("*")
      .eq("token", token)
      .single();

    if (tokenError || !tokenRow) {
      throw new Error("Invalid or expired download token.");
    }

    // 2. Expiry Check
    if (new Date(tokenRow.expires_at) < new Date()) {
      throw new Error("Token has expired. Please generate a new one.");
    }

    // 3. Usage & IP Locking Check
    if (tokenRow.is_used) {
        throw new Error("This download link has already been used.");
    }

    // Strict IP Locking
    if (tokenRow.ip_address && tokenRow.ip_address !== clientIp) {
      throw new Error("Download link is locked to a different IP address.");
    }

    // 4. Content Retrieval Details
    const table = tokenRow.content_type === "track" ? "tracks" : "album_packs";
    const { data: content } = await supabaseAdmin
      .from(table)
      .select("file_key, title, dj_id")
      .eq("id", tokenRow.content_id)
      .single();

    if (!content) throw new Error("Content not found");

    return { tokenRow, content };
  }

  /**
   * Mark token as used and handle quota
   */
  static async markAsUsed(token: string, tokenRow: any) {
    // 5. Atomic Usage Mark
    // We only update if is_used is still false.
    const { data: updatedToken, error: updateError } = await supabaseAdmin
      .from("download_tokens")
      .update({ 
          is_used: true
      })
      .eq("token", token)
      .eq("is_used", false)
      .select();

    if (updateError || !updatedToken || updatedToken.length === 0) {
        throw new Error("This download link has already been used or is invalid.");
    }

    // 6. Handle Subscription Quota Decrement
    if (tokenRow.access_source === "subscription") {
        const table = tokenRow.content_type === "track" ? "tracks" : "album_packs";
        const { data: sub } = await supabaseAdmin
            .from("dj_subscriptions")
            .select("id, dj_id")
            .eq("user_id", tokenRow.user_id)
            .eq("dj_id", (await supabaseAdmin.from(table).select("dj_id").eq("id", tokenRow.content_id).single()).data?.dj_id)
            .gt("expires_at", new Date().toISOString())
            .single();

        if (sub) {
            const quotaField = tokenRow.content_type === "track" ? "tracks_used" : "zip_used";
            await supabaseAdmin.rpc('increment_subscription_usage', {
                sub_id: sub.id,
                field_name: quotaField
            });
        }
    }
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
