'use client';

import { ActivityFeed } from '@/components/features/social/ActivityFeed';
import { PlaylistManager } from '@/components/features/social/PlaylistManager';
import { Share2, Users, MessageSquare } from 'lucide-react';

export default function SocialPage() {
    return (
        <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center gap-4 mb-2">
                <div className="p-3 bg-pink-500/10 rounded-2xl border border-pink-500/20 shadow-pink-glow">
                    <Share2 className="w-8 h-8 text-pink-400" />
                </div>
                <div>
                    <h1 className="text-3xl font-heading font-bold text-white">Social & Community</h1>
                    <p className="text-zinc-400">Stay connected with your favorite DJs and the MixMint community.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-8">
                    <PlaylistManager />
                </div>
                <div className="space-y-8">
                    <ActivityFeed />

                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <MessageSquare size={120} />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Community Stats</h3>
                        <div className="space-y-4 relative z-10">
                            <div className="flex justify-between items-center p-3 bg-zinc-950 rounded-xl border border-zinc-800">
                                <span className="text-zinc-400 text-sm">Comments Posted</span>
                                <span className="text-white font-bold">0</span>
                            </div>
                            <div className="flex justify-between items-center p-3 bg-zinc-950 rounded-xl border border-zinc-800">
                                <span className="text-zinc-400 text-sm">Active Playlists</span>
                                <span className="text-white font-bold">0</span>
                            </div>
                            <div className="flex justify-between items-center p-3 bg-zinc-950 rounded-xl border border-zinc-800">
                                <span className="text-zinc-400 text-sm">Friends / Following</span>
                                <span className="text-white font-bold">0</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
