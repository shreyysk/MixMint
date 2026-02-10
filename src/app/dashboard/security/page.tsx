'use client';

import { MFAManager } from '@/components/features/dashboard/MFAManager';
import { DeviceManager } from '@/components/features/dashboard/DeviceManager';
import { LoginHistory } from '@/components/features/dashboard/LoginHistory';
import { PrivacyControls } from '@/components/features/compliance/PrivacyControls';
import { Shield } from 'lucide-react';

export default function SecurityPage() {
    return (
        <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center gap-4 mb-2">
                <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-purple-glow">
                    <Shield className="w-8 h-8 text-purple-400" />
                </div>
                <div>
                    <h1 className="text-3xl font-heading font-bold text-white">Security & Privacy</h1>
                    <p className="text-zinc-400">Manage your account protection, authorized devices, and session history.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-8">
                    <MFAManager />
                    <DeviceManager />
                </div>
                <div className="h-fit">
                    <LoginHistory />
                </div>
            </div>

            <div className="border-t border-zinc-900 pt-8 mt-8">
                <PrivacyControls />
            </div>
        </div>
    );
}
