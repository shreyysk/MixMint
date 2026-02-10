
import { supabaseAdmin } from "@/lib/supabaseServer";

export type SuspiciousActivityType = 
    | "concurrent_download_limit_exceeded"
    | "rapid_download_pattern"
    | "multiple_ip_access";

export class SuspiciousActivityService {
    /**
     * Log a suspicious event to the audit_logs table.
     */
    static async log(
        type: SuspiciousActivityType,
        metadata: {
            userId: string;
            ipAddress?: string;
            userAgent?: string;
            resourceId?: string; // e.g. content_id
            description?: string;
        }
    ) {
        const { userId, ipAddress, userAgent, resourceId, description } = metadata;

        try {
           const { error } = await supabaseAdmin
            .from("audit_logs")
            .insert({
                action: "SUSPICIOUS_ACTIVITY",
                target_id: userId, // The user being flagged
                metadata: {
                    type,
                    ip_address: ipAddress,
                    user_agent: userAgent,
                    resource_id: resourceId,
                    description: description || "Suspicious activity detected"
                }
            });

            if (error) {
                console.error("[SUSPICIOUS_ACTIVITY_LOG_ERROR]", error);
            }
        } catch (err) {
            console.error("[SUSPICIOUS_ACTIVITY_SERVICE_ERROR]", err);
        }
    }
}
