'use client';

import React from 'react';
import { Lock, Hammer, Shield } from 'lucide-react';

export default function MaintenancePage() {
    return (
        <div className="min-h-screen bg-black flex flex-col items-center justify-center p-6 text-center">
            <div className="relative mb-8">
                <div className="absolute inset-0 bg-red-500/20 blur-3xl rounded-full" />
                <div className="relative p-6 bg-zinc-900/50 border border-zinc-800 rounded-3xl shadow-2xl">
                    <Lock className="w-16 h-16 text-red-500 animate-pulse" />
                </div>
            </div>

            <h1 className="text-4xl font-heading font-black text-white mb-4 tracking-tighter">
                PLATFORM UNDER MAINTENANCE
            </h1>

            <p className="text-zinc-400 max-w-md mx-auto mb-8 leading-relaxed">
                MixMint is currently undergoing scheduled upgrades to improve your experience.
                Our engineers are working hard to bring you new features.
            </p>

            <div className="flex items-center gap-6 p-1 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 pr-6">
                <div className="p-3 bg-zinc-800 rounded-xl">
                    <Hammer className="w-5 h-5 text-red-400" />
                </div>
                <div className="text-left">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Estimated Duration</p>
                    <p className="text-sm font-bold text-white">~ 2 hours</p>
                </div>
            </div>

            <div className="mt-12 flex items-center gap-2 text-zinc-600">
                <Shield size={14} />
                <span className="text-[10px] font-bold uppercase tracking-widest letter-spacing-widest">MixMint Guardian Active</span>
            </div>
        </div>
    );
}
