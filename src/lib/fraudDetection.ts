import { supabaseServer } from "./supabaseServer";
import { logger } from "./logger";

/**
 * MixMint Fraud Detection System
 * Detects and flags suspicious patterns across referrals, downloads, and payments
 */

export type FraudAlertType = 'referral_abuse' | 'download_farming' | 'payment_fraud' | 'suspicious_activity';
export type FraudSeverity = 'low' | 'medium' | 'high' | 'critical';

/**
 * createFraudAlert
 * Creates a new fraud alert for admin review
 */
export async function createFraudAlert(
    userId: string,
    alertType: FraudAlertType,
    severity: FraudSeverity,
    details: Record<string, any>
) {
    try {
        const { error } = await supabaseServer
            .from('fraud_alerts')
            .insert({
                user_id: userId,
                alert_type: alertType,
                severity,
                details,
                status: 'pending'
            });

        if (error) throw error;

        logger.warn("SECURITY", `Fraud alert created: ${alertType}`, { userId, severity, details });
    } catch (err) {
        logger.error("SECURITY", "Failed to create fraud alert", err, { userId, alertType });
    }
}

/**
 * detectReferralAbuse
 * Checks for suspicious referral patterns
 */
export async function detectReferralAbuse(userId: string) {
    try {
        // 1. Check for multiple signups from same IP
        const { data: recentSignups } = await supabaseServer
            .from('login_history')
            .select('user_id, ip_address')
            .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
            .eq('ip_address', (await getUserLastIP(userId)));

        if (recentSignups && recentSignups.length > 3) {
            await createFraudAlert(
                userId,
                'referral_abuse',
                'high',
                { reason: 'Multiple signups from same IP', count: recentSignups.length }
            );
        }

        // 2. Check for circular referrals
        const { data: referrals } = await supabaseServer
            .from('referrals')
            .select('referrer_id, referred_id')
            .or(`referrer_id.eq.${userId},referred_id.eq.${userId}`);

        if (referrals && referrals.length > 0) {
            const referrerIds = referrals.filter(r => r.referred_id === userId).map(r => r.referrer_id);
            const referredIds = referrals.filter(r => r.referrer_id === userId).map(r => r.referred_id);

            // Check if any referred user also referred this user
            const circular = referrerIds.some(id => referredIds.includes(id));
            if (circular) {
                await createFraudAlert(
                    userId,
                    'referral_abuse',
                    'critical',
                    { reason: 'Circular referral pattern detected' }
                );
            }
        }

        // 3. Check for referrals with no purchase history
        const { data: referredUsers } = await supabaseServer
            .from('referrals')
            .select('referred_id')
            .eq('referrer_id', userId)
            .gte('created_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString());

        if (referredUsers && referredUsers.length > 5) {
            const { count } = await supabaseServer
                .from('purchases')
                .select('*', { count: 'exact', head: true })
                .in('user_id', referredUsers.map(r => r.referred_id));

            if (count === 0) {
                await createFraudAlert(
                    userId,
                    'referral_abuse',
                    'medium',
                    { reason: 'Multiple referrals with no purchases', referralCount: referredUsers.length }
                );
            }
        }

    } catch (err) {
        logger.error("SECURITY", "Referral abuse detection failed", err, { userId });
    }
}

/**
 * detectDownloadFarming
 * Checks for excessive download attempts
 */
export async function detectDownloadFarming(userId: string, contentId: string) {
    try {
        // 1. Check download frequency
        const { count } = await supabaseServer
            .from('download_tokens')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', userId)
            .gte('created_at', new Date(Date.now() - 60 * 60 * 1000).toISOString()); // Last hour

        if (count && count > 10) {
            await createFraudAlert(
                userId,
                'download_farming',
                'high',
                { reason: 'Excessive downloads in short period', count }
            );
        }

        // 2. Check for token sharing (same content, different IPs)
        const { data: tokens } = await supabaseServer
            .from('download_tokens')
            .select('ip_address')
            .eq('user_id', userId)
            .eq('content_id', contentId)
            .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString());

        if (tokens) {
            const uniqueIPs = new Set(tokens.map(t => t.ip_address));
            if (uniqueIPs.size > 3) {
                await createFraudAlert(
                    userId,
                    'download_farming',
                    'critical',
                    { reason: 'Token sharing detected', ipCount: uniqueIPs.size }
                );
            }
        }

    } catch (err) {
        logger.error("SECURITY", "Download farming detection failed", err, { userId });
    }
}

/**
 * detectPaymentFraud
 * Checks for suspicious payment patterns
 */
export async function detectPaymentFraud(userId: string, paymentId: string) {
    try {
        // 1. Check for rapid retry attempts
        const { count } = await supabaseServer
            .from('purchases')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', userId)
            .gte('created_at', new Date(Date.now() - 10 * 60 * 1000).toISOString()); // Last 10 minutes

        if (count && count > 5) {
            await createFraudAlert(
                userId,
                'payment_fraud',
                'medium',
                { reason: 'Rapid payment retry attempts', count }
            );
        }

        // 2. Check for geographic anomalies (if IP country data available)
        // This would require IP geolocation service integration

    } catch (err) {
        logger.error("SECURITY", "Payment fraud detection failed", err, { userId });
    }
}

/**
 * Helper: Get user's last known IP
 */
async function getUserLastIP(userId: string): Promise<string | null> {
    const { data } = await supabaseServer
        .from('login_history')
        .select('ip_address')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

    return data?.ip_address || null;
}
