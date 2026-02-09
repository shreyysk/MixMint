"use client";

import { cn } from "@/lib/utils";
import { TrendingUp } from "lucide-react";
import Link from "next/link";

interface QuotaTrackerProps {
    djName: string;
    plan: string;
    used: number;
    total: number;
    daysRemaining: number;
    djSlug?: string;
    className?: string;
}

export function QuotaTracker({
    djName,
    plan,
    used,
    total,
    daysRemaining,
    djSlug,
    className
}: QuotaTrackerProps) {
    const percentage = Math.min((used / total) * 100, 100);
    const isAlmostDone = percentage >= 80;

    return (
        <div className={cn(
            "p-4 rounded-2xl bg-surface-dark border border-white/5",
            className
        )}>
            <div className="flex items-center justify-between mb-3">
                <div>
                    <h4 className="font-heading font-bold text-white text-sm">{djName}</h4>
                    <p className="text-xs text-zinc-500 capitalize">{plan} Plan</p>
                </div>
                {djSlug && (
                    <Link
                        href={`/dj/${djSlug}`}
                        className="text-purple-primary hover:text-purple-primary-dark transition-colors"
                    >
                        <TrendingUp size={16} />
                    </Link>
                )}
            </div>

            {/* Progress Bar */}
            <div className="progress-quota mb-2">
                <div
                    className="progress-quota-fill"
                    style={{ width: `${percentage}%` }}
                />
            </div>

            <div className="flex items-center justify-between text-xs">
                <span className={cn(
                    "font-accent font-semibold",
                    isAlmostDone ? "text-gold" : "text-mint-accent"
                )}>
                    {used}/{total} tracks
                </span>
                <span className="text-zinc-500">
                    Resets in {daysRemaining} days
                </span>
            </div>

            {isAlmostDone && (
                <Link
                    href="/pricing"
                    className="mt-3 block text-center text-xs font-semibold text-purple-primary hover:text-purple-primary-dark transition-colors"
                >
                    Upgrade to Super →
                </Link>
            )}
        </div>
    );
}
