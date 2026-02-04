import React from "react";
import { ShoppingBag, Users, Download } from "lucide-react";

interface QuickStatsProps {
    totalPurchases: number;
    activeSubscriptions: number;
    totalDownloads: number;
}

export function QuickStats({ totalPurchases, activeSubscriptions, totalDownloads }: QuickStatsProps) {
    const stats = [
        {
            icon: ShoppingBag,
            label: "Purchases",
            value: totalPurchases,
            color: "text-emerald-400",
            bg: "bg-emerald-600/10",
            border: "border-emerald-500/30",
        },
        {
            icon: Users,
            label: "Active Subscriptions",
            value: activeSubscriptions,
            color: "text-violet-400",
            bg: "bg-violet-600/10",
            border: "border-violet-500/30",
        },
        {
            icon: Download,
            label: "Available Downloads",
            value: totalDownloads,
            color: "text-amber-400",
            bg: "bg-amber-600/10",
            border: "border-amber-500/30",
        },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-8">
            {stats.map((stat) => {
                const Icon = stat.icon;
                return (
                    <div
                        key={stat.label}
                        className={`p-6 rounded-2xl ${stat.bg} border ${stat.border} backdrop-blur-sm`}
                    >
                        <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl ${stat.bg} border ${stat.border} flex items-center justify-center ${stat.color}`}>
                                <Icon size={24} />
                            </div>
                            <div>
                                <p className="text-sm text-zinc-500 font-semibold mb-1">{stat.label}</p>
                                <p className={`text-3xl font-extrabold ${stat.color}`}>{stat.value}</p>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
