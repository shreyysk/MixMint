"use client";

import React, { useEffect, useState } from "react";
import { PointsStats } from "./PointsStats";
import { ReferralLink } from "./ReferralLink";
import { PointsHistory } from "./PointsHistory";
import { Info, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export function RewardsDashboard() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    async function fetchData() {
        try {
            setLoading(true);
            const [pointsRes, refRes] = await Promise.all([
                fetch('/api/rewards/points'),
                fetch('/api/rewards/referral')
            ]);

            const pointsJson = await pointsRes.json();
            const refJson = await refRes.json();

            if (!pointsRes.ok) throw new Error(pointsJson.error || "Failed to load points");
            if (!refRes.ok) throw new Error(refJson.error || "Failed to load referrals");

            setData({
                points: pointsJson.data,
                referral: refJson.data
            });
        } catch (err: any) {
            console.error("[REWARDS_DASHBOARD_ERROR]:", err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    if (loading) return (
        <div className="flex items-center justify-center py-20">
            <Loader2 className="animate-spin text-violet-400" size={40} />
        </div>
    );

    if (error) return (
        <div className="p-8 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-center italic font-bold">
            {error}
        </div>
    );

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-12"
        >
            {/* Informational Banner */}
            <div className="bg-violet-600/10 border border-violet-500/20 p-6 rounded-3xl flex items-start gap-4 backdrop-blur-sm">
                <div className="w-10 h-10 rounded-xl bg-violet-600/20 flex items-center justify-center shrink-0">
                    <Info className="text-violet-400" size={20} />
                </div>
                <div>
                    <h4 className="text-sm font-black text-white uppercase tracking-tight mb-1 italic">Points & Multipliers</h4>
                    <p className="text-xs text-zinc-500 font-bold leading-relaxed italic">
                        Points are earned through activity and referrals. Use them in the future for
                        exclusive track discounts, subscription credits, and profile badges. Redemption functionality coming soon!
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                <div className="lg:col-span-2 space-y-12">
                    <PointsStats
                        balance={data.points.balance}
                        totalEarned={data.points.totalEarned}
                    />
                    <PointsHistory history={data.points.history} />
                </div>

                <div>
                    <ReferralLink
                        code={data.referral.code}
                        link={data.referral.link}
                        stats={data.referral.stats}
                    />
                </div>
            </div>
        </motion.div>
    );
}
