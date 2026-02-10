'use client';

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';

export default function MaintenanceGuard({ children }: { children: React.ReactNode }) {
    const [isMaintenance, setIsMaintenance] = useState(false);
    const [isAdmin, setIsAdmin] = useState(false);
    const [loading, setLoading] = useState(true);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        checkMaintenance();
    }, [pathname]);

    async function checkMaintenance() {
        try {
            // 1. Fetch Maintenance Status
            const { data: settings, error } = await supabase
                .from('system_settings')
                .select('value')
                .eq('key', 'maintenance_mode')
                .single();

            if (error) throw error;
            const enabled = settings?.value?.enabled || false;
            setIsMaintenance(enabled);

            // 2. Fetch User Role
            let currentRole = null;
            const { data: { user } } = await supabase.auth.getUser();
            if (user) {
                const { data: profile } = await supabase
                    .from('profiles')
                    .select('role')
                    .eq('id', user.id)
                    .single();
                currentRole = profile?.role;
                setIsAdmin(currentRole === 'admin');
            }

            // 3. Logic: If maintenance is ON and NOT admin and NOT on maintenance page -> Redirect
            if (enabled && currentRole !== 'admin' && pathname !== '/maintenance') {
                router.push('/maintenance');
            } else if (!enabled && pathname === '/maintenance') {
                router.push('/');
            }
        } catch (err) {
            console.error('[MAINTENANCE_CHECK_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    // Skip guard for admin paths/api or if loading isn't critical for simple view
    if (loading) return null;

    return <>{children}</>;
}
