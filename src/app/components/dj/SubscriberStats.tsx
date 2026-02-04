import React from "react";
import { Users, Star, Zap, Crown, CheckCircle, XCircle } from "lucide-react";

interface SubscriberStatsProps {
    totalSubscribers: number;
    basicCount: number;
    proCount: number;
    superCount: number;
    activeCount: number;
    expiredCount: number;
}

export function SubscriberStats({
    totalSubscribers,
    basicCount,
    proCount,
    superCount,
    activeCount,
    expiredCount,
}: SubscriberStatsProps) {
    const plans = [
        {
            name: 'Basic',
            count: basicCount,
            icon: Star,
            color: 'text-zinc-400',
            bg: 'bg-zinc-600/20',
            border: 'border-zinc-500/40',
            barColor: 'from-zinc-600 to-zinc-500',
        },
        {
            name: 'Pro',
            count: proCount,
            icon: Zap,
            color: 'text-violet-400',
            bg: 'bg-violet-600/20',
            border: 'border-violet-500/40',
            barColor: 'from-violet-600 to-violet-500',
        },
        {
            name: 'Super',
            count: superCount,
            icon: Crown,
            color: 'text-amber-400',
            bg: 'bg-amber-600/20',
            border: 'border-amber-500/40',
            barColor: 'from-amber-600 to-amber-500',
        },
    ];

    const getPercentage = (count: number) => {
        return totalSubscribers > 0 ? Math.round((count / totalSubscribers) * 100) : 0;
    };

    return (
        <div className="space-y-6">
            {/* Total Subscribers - Large Display */}
            <div className="p-8 rounded-2xl bg-gradient-to-br from-violet-600/20 to-violet-600/5 border border-violet-500/40 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-14 h-14 rounded-xl bg-violet-600/30 border border-violet-500/50 flex items-center justify-center">
                        <Users className="text-violet-400" size={28} />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-violet-400 uppercase tracking-wide">
                            Total Subscribers
                        </p>
                        <h2 className="text-4xl md:text-5xl font-extrabold text-white">
                            {totalSubscribers}
                        </h2>
                    </div>
                </div>
                <p className="text-sm text-zinc-500">
                    Fans who have subscribed to your content
                </p>
            </div>

            {/* Active vs Expired */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Active */}
                <div className="p-6 rounded-2xl bg-emerald-600/10 border border-emerald-500/30 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-12 h-12 rounded-xl bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center">
                            <CheckCircle className="text-emerald-400" size={20} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-zinc-500">Active</p>
                            <h3 className="text-2xl font-extrabold text-white">
                                {activeCount}
                            </h3>
                        </div>
                    </div>
                </div>

                {/* Expired */}
                <div className="p-6 rounded-2xl bg-red-600/10 border border-red-500/30 backdrop-blur-sm">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-12 h-12 rounded-xl bg-red-600/20 border border-red-500/40 flex items-center justify-center">
                            <XCircle className="text-red-400" size={20} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-zinc-500">Expired</p>
                            <h3 className="text-2xl font-extrabold text-white">
                                {expiredCount}
                            </h3>
                        </div>
                    </div>
                </div>
            </div>

            {/* Plan Breakdown */}
            <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 backdrop-blur-sm">
                <h3 className="text-lg font-bold text-white mb-4">Plan Breakdown</h3>
                <div className="space-y-4">
                    {plans.map((plan) => {
                        const Icon = plan.icon;
                        const percentage = getPercentage(plan.count);

                        return (
                            <div key={plan.name}>
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <Icon className={plan.color} size={16} />
                                        <span className="text-sm font-bold text-zinc-400">{plan.name}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-sm font-extrabold text-white">{plan.count}</span>
                                        <span className={`text-xs font-bold ${plan.color}`}>{percentage}%</span>
                                    </div>
                                </div>
                                <div className="h-2 bg-zinc-800/60 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full bg-gradient-to-r ${plan.barColor}`}
                                        style={{ width: `${percentage}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
