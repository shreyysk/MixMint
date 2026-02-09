import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

export type AuditActionType = 
    | 'update_setting'
    | 'ban_user'
    | 'unban_user'
    | 'approve_dj'
    | 'reject_dj'
    | 'delete_track'
    | 'feature_dj'
    | 'manual_refund';

export type AuditEntityType = 'user' | 'track' | 'system' | 'payment' | 'subscription';

interface LogAuditParams {
    adminId: string;
    action: AuditActionType;
    entityType: AuditEntityType;
    entityId?: string;
    details?: any;
    ip?: string;
}

export async function logAdminAction({
    adminId,
    action,
    entityType,
    entityId,
    details,
    ip
}: LogAuditParams) {
    try {
        const { error } = await supabaseServer
            .from('admin_audit_logs')
            .insert({
                admin_id: adminId,
                action_type: action,
                entity_type: entityType,
                entity_id: entityId,
                details,
                ip_address: ip
            });

        if (error) {
            logger.error("ADMIN", "Failed to log admin action", error, { adminId, action });
        }
    } catch (err) {
        logger.error("ADMIN", "Exception logging admin action", err, { adminId, action });
    }
}
