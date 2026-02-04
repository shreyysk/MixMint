"use client";

import React, { useEffect, useState } from "react";
import { ReferralLink } from "../rewards/ReferralLink";
import { Loader2, Users, Trophy, Info, Star } from "lucide-react";
import { motion } from "framer-motion";

export function DJReferralSummary() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    async function fetchData() {
        try {
            setLoading(true);
            const res = await fetch('/api/rewards/referral');
            const json = await res.json();
            if (!res.ok) throw new Error(json.error || "Failed to load referral info");
            setData(json.data);
        } catch (err: any) {
            console.error("[DJ_REFERRAL_ERROR]:", err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    if (loading) return (
        <div className="flex justify-center py-20">
            <Loader2 className="animate-spin text-violet-400" size={40} />
        </div>
    );

    if (error) return (
        <div className="p-8 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-center italic font-bold">
            {error}
        </div>
    );

    return (
        <div className="space-y-12">
            <div className="bg-amber-600/10 border border-amber-500/20 p-6 rounded-3xl flex items-start gap-4 backdrop-blur-sm">
                <div className="w-10 h-10 rounded-xl bg-amber-600/20 flex items-center justify-center shrink-0 border border-amber-500/20">
                    <Trophy className="text-amber-400" size={20} />
                </div>
                <div>
                    <h4 className="text-sm font-black text-white uppercase tracking-tight mb-1 italic">Exclusive DJ referral Program</h4>
                    <p className="text-xs text-zinc-500 font-bold leading-relaxed italic">
                        Invite fellow creators to MixMint. DJs who refer more than 5 others get
                        featured on the Explore page and lower platform fees. Points earned contribute to your platform seniority.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                <div className="lg:col-span-2 space-y-8">
                    <h3 className="text-2xl font-black text-white uppercase italic tracking-tighter">Grow the MixMint Creator Ecosystem</h3>
                    <p className="text-zinc-500 font-medium italic leading-relaxed">
                        MixMint is built for DJs, by DJs. When you invite your circle, you help us build a more
                        sustainable economy for independent music globally. Earn points and platform status
                        for every successful onboarding.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800 backdrop-blur-xl group">
                            <div className="w-12 h-12 rounded-2xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <Users className="text-violet-400" size={24} />
                            </div>
                            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">Network Size</p>
                            <p className="text-4xl font-black text-white italic tracking-tighter">{data.stats.totalInvites}</p>
                            <p className="text-xs text-zinc-600 font-bold italic mt-2">DJs joined using your link</p>
                        </div>

                        <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800 backdrop-blur-xl group">
                            <div className="w-12 h-12 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <Star className="text-emerald-400" size={24} />
                            </div>
                            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">Conversion Rate</p>
                            <p className="text-4xl font-black text-white italic tracking-tighter">
                                {data.stats.totalInvites > 0 ? Math.round((data.stats.successfulReferrals / data.stats.totalInvites) * 100) : 0}%
                            </p>
                            <p className="text-xs text-zinc-600 font-bold italic mt-2">Verified creators refers</p>
                        </div>
                    </div>

                    <div className="p-6 rounded-2xl bg-zinc-900/20 border border-zinc-800/50 border-dashed">
                        <p className="text-center text-xs text-zinc-600 font-bold uppercase tracking-widest italic">
                            Referral rewards are distributed within 24 hours of verified profile setup.
                        </p>
                    </div>
                </div>

                <div>
                    <ReferralLink
                        code={data.code}
                        link={data.link}
                        stats={data.stats}
                        description={
                            <>
                                Share your DJ invite link and earn <span className="text-amber-500">100 Pts</span> for every
                                onboarded DJ who uploads their first track.
                            </>
                        }
                    />
                </div>
            </div>
        </div>
    );
}
