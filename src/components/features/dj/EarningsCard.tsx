import React from "react";
import { DollarSign, TrendingUp, Music, Package } from "lucide-react";

interface EarningsCardProps {
    totalEarnings: number;
    monthlyEarnings: number;
    trackEarnings: number;
    albumEarnings: number;
}

export function EarningsCard({
    totalEarnings,
    monthlyEarnings,
    trackEarnings,
    albumEarnings,
}: EarningsCardProps) {
    const formatCurrency = (amount: number) => {
        return `₹${amount.toLocaleString('en-IN')}`;
    };

    const trackPercentage = totalEarnings > 0
        ? Math.round((trackEarnings / totalEarnings) * 100)
        : 0;

    const albumPercentage = totalEarnings > 0
        ? Math.round((albumEarnings / totalEarnings) * 100)
        : 0;

    return (
        <div className="space-y-6">
            {/* Total Earnings - Large Display */}
            <div className="p-8 rounded-2xl bg-gradient-to-br from-emerald-600/20 to-emerald-600/5 border border-emerald-500/40 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-14 h-14 rounded-xl bg-emerald-600/30 border border-emerald-500/50 flex items-center justify-center">
                        <DollarSign className="text-emerald-400" size={28} />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-emerald-400 uppercase tracking-wide">
                            Total Lifetime Earnings
                        </p>
                        <h2 className="text-4xl md:text-5xl font-extrabold text-white">
                            {formatCurrency(totalEarnings)}
                        </h2>
                    </div>
                </div>
                <p className="text-sm text-zinc-500">
                    Accumulated from all track and album sales
                </p>
            </div>

            {/* Monthly Earnings */}
            <div className="p-6 rounded-2xl bg-violet-600/10 border border-violet-500/30 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-12 h-12 rounded-xl bg-violet-600/20 border border-violet-500/40 flex items-center justify-center">
                        <TrendingUp className="text-violet-400" size={20} />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-zinc-500">This Month</p>
                        <h3 className="text-2xl font-extrabold text-white">
                            {formatCurrency(monthlyEarnings)}
                        </h3>
                    </div>
                </div>
            </div>

            {/* Breakdown by Type */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Track Earnings */}
                <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
                            <Music className="text-violet-400" size={18} />
                        </div>
                        <p className="text-sm font-bold text-zinc-400">Track Sales</p>
                    </div>
                    <h4 className="text-2xl font-extrabold text-white mb-2">
                        {formatCurrency(trackEarnings)}
                    </h4>
                    <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-violet-600 to-violet-500"
                                style={{ width: `${trackPercentage}%` }}
                            />
                        </div>
                        <span className="text-xs font-bold text-violet-400">{trackPercentage}%</span>
                    </div>
                </div>

                {/* Album Earnings */}
                <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-lg bg-amber-600/20 border border-amber-500/30 flex items-center justify-center">
                            <Package className="text-amber-400" size={18} />
                        </div>
                        <p className="text-sm font-bold text-zinc-400">Album Sales</p>
                    </div>
                    <h4 className="text-2xl font-extrabold text-white mb-2">
                        {formatCurrency(albumEarnings)}
                    </h4>
                    <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-amber-600 to-amber-500"
                                style={{ width: `${albumPercentage}%` }}
                            />
                        </div>
                        <span className="text-xs font-bold text-amber-400">{albumPercentage}%</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
