import { supabaseServer } from "../supabaseServer";
import { logger } from "../logger";

/**
 * logLogin
 * Records a login event and checks for basic suspicious activity (IP change).
 */
export async function logLogin(userId: string, ip: string, userAgent: string) {
    try {
        // 1. Check for last seen IP
        const { data: lastLogin } = await supabaseServer
            .from('login_history')
            .select('ip_address, created_at')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(1)
            .single();

        let isSuspicious = false;
        if (lastLogin && lastLogin.ip_address !== ip) {
            isSuspicious = true;
        }

        // 2. Record Login
        const { error } = await supabaseServer
            .from('login_history')
            .insert({
                user_id: userId,
                ip_address: ip,
                user_agent: userAgent,
                is_suspicious: isSuspicious
            });

        if (error) throw error;

        if (isSuspicious) {
            logger.warn("SECURITY", "Suspicious login detected", { userId, ip, lastIp: lastLogin?.ip_address });
            // In a real app, send an email: sendAlertEmail(userId, 'suspicious_login', { ip, userAgent });
        }

        return { success: true, isSuspicious };
    } catch (err) {
        logger.error("SECURITY", "Failed to log login", err, { userId, ip });
        return { success: false };
    }
}

/**
 * registerDevice
 * Enforces the 3-device limit and registers/updates a device fingerprint.
 */
export async function registerDevice(userId: string, fingerprint: string, label: string, ip: string) {
    try {
        // 1. Check authorized device mapping
        const { data: devices } = await supabaseServer
            .from('user_devices')
            .select('id, fingerprint, status')
            .eq('user_id', userId)
            .eq('status', 'authorized');

        const existingDevice = devices?.find(d => d.fingerprint === fingerprint);

        if (existingDevice) {
            // Update last active
            await supabaseServer
                .from('user_devices')
                .update({ last_ip: ip, last_active_at: new Date().toISOString() })
                .eq('id', existingDevice.id);
            
            return { success: true, deviceId: existingDevice.id };
        }

        // 2. Check limit
        if (devices && devices.length >= 3) {
            return { success: false, error: "Device limit reached (max 3). Manage your devices in settings." };
        }

        // 3. Register New Device
        const { data: newDevice, error: regError } = await supabaseServer
            .from('user_devices')
            .insert({
                user_id: userId,
                fingerprint: fingerprint,
                label: label,
                last_ip: ip,
                status: 'authorized'
            })
            .select()
            .single();

        if (regError) throw regError;

        return { success: true, deviceId: newDevice.id };
    } catch (err) {
        logger.error("SECURITY", "Failed to register device", err, { userId, fingerprint });
        return { success: false, error: "Device registration failed" };
    }
}
