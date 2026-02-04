import React from "react";
import Link from "next/link";
import { Users, Calendar, Music, Package, Upload } from "lucide-react";
import { Button } from "@/app/components/ui/Button";

interface SubscriptionCardProps {
    id: string;
    djName: string;
    djSlug: string;
    plan: 'basic' | 'pro' | 'super';
    expiresAt: string;
    isActive: boolean;
    trackQuota: number;
    zipQuota: number;
    fanUploadQuota?: number;
}

export function SubscriptionCard({
    id,
    djName,
    djSlug,
    plan,
    expiresAt,
    isActive,
    trackQuota,
    zipQuota,
    fanUploadQuota,
}: SubscriptionCardProps) {
    const planConfig = {
        basic: {
            name: 'Basic',
            color: 'text-zinc-400',
            bg: 'bg-zinc-600/20',
            border: 'border-zinc-500/40',
        },
        pro: {
            name: 'Pro',
            color: 'text-violet-400',
            bg: 'bg-violet-600/20',
            border: 'border-violet-500/40',
        },
        super: {
            name: 'Super',
            color: 'text-amber-400',
            bg: 'bg-amber-600/20',
            border: 'border-amber-500/40',
        },
    };

    const config = planConfig[plan];

    // Format date
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    // Calculate days remaining
    const daysRemaining = () => {
        const now = new Date();
        const expiry = new Date(expiresAt);
        const diff = expiry.getTime() - now.getTime();
        const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
        return days;
    };

    const days = daysRemaining();

    return (
        <div className={`group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border ${isActive ? 'border-emerald-500/40' : 'border-red-500/40'} transition-all duration-300 p-6`}>
            <div className="flex items-start justify-between gap-4 mb-4">
                {/* DJ Icon */}
                <div className="w-12 h-12 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shrink-0">
                    <Users className="text-violet-400" size={20} />
                </div>

                {/* Status Badge */}
                <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold uppercase tracking-wider ${isActive
                        ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-400'
                        : 'bg-red-600/20 border-red-500/40 text-red-400'
                    }`}>
                    {isActive ? 'Active' : 'Expired'}
                </div>
            </div>

            {/* DJ Name */}
            <Link
                href={`/dj/${djSlug}`}
                className="block mb-3"
            >
                <h3 className="text-xl font-bold text-white hover:text-violet-400 transition-colors">
                    {djName}
                </h3>
            </Link>

            {/* Plan Badge */}
            <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${config.bg} ${config.border} ${config.color} text-sm font-bold mb-4`}>
                {config.name} Plan
            </div>

            {/* Expiry Info */}
            <div className="mb-4 pb-4 border-b border-zinc-800/60">
                <div className="flex items-center gap-2 text-sm text-zinc-500 mb-1">
                    <Calendar size={14} />
                    <span className="font-semibold">
                        {isActive ? 'Expires' : 'Expired'}: {formatDate(expiresAt)}
                    </span>
                </div>
                {isActive && days > 0 && (
                    <p className="text-xs text-zinc-600 ml-5">
                        {days} {days === 1 ? 'day' : 'days'} remaining
                    </p>
                )}
            </div>

            {/* Quotas */}
            <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-zinc-500 flex items-center gap-2">
                        <Music size={14} />
                        Track Downloads
                    </span>
                    <span className="text-white font-bold">
                        {trackQuota === -1 ? 'Unlimited' : trackQuota}
                    </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                    <span className="text-zinc-500 flex items-center gap-2">
                        <Package size={14} />
                        Album Packs
                    </span>
                    <span className="text-white font-bold">
                        {zipQuota === -1 ? 'Unlimited' : zipQuota}
                    </span>
                </div>
                {fanUploadQuota !== undefined && (
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-zinc-500 flex items-center gap-2">
                            <Upload size={14} />
                            Fan Uploads
                        </span>
                        <span className="text-white font-bold">
                            {fanUploadQuota === -1 ? 'Unlimited' : fanUploadQuota}
                        </span>
                    </div>
                )}
            </div>

            {/* View DJ Button */}
            <Link href={`/dj/${djSlug}`}>
                <Button variant="outline" size="sm" className="w-full">
                    View DJ Profile
                </Button>
            </Link>
        </div>
    );
}
