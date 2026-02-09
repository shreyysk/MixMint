import React from "react";
import { Check, Lock, Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface AccessBadgeProps {
    variant: 'owned' | 'subscribed' | 'locked';
    className?: string;
}

export function AccessBadge({ variant, className }: AccessBadgeProps) {
    const styles = {
        owned: {
            bg: 'bg-emerald-600/20',
            border: 'border-emerald-500/40',
            text: 'text-emerald-400',
            icon: Check,
            label: 'Owned',
        },
        subscribed: {
            bg: 'bg-violet-600/20',
            border: 'border-violet-500/40',
            text: 'text-violet-400',
            icon: Star,
            label: 'Subscribed',
        },
        locked: {
            bg: 'bg-red-600/20',
            border: 'border-red-500/40',
            text: 'text-red-400',
            icon: Lock,
            label: 'Locked',
        },
    };

    const style = styles[variant];
    const Icon = style.icon;

    return (
        <div className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold uppercase tracking-wider",
            style.bg,
            style.border,
            style.text,
            className
        )}>
            <Icon size={12} />
            <span>{style.label}</span>
        </div>
    );
}
