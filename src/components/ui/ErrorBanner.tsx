import React from "react";
import { AlertCircle, AlertTriangle, X } from "lucide-react";
import { Button } from "./Button";

interface ErrorBannerProps {
    title: string;
    message: string;
    action?: {
        label: string;
        onClick: () => void;
    };
    variant?: 'error' | 'warning';
    onDismiss?: () => void;
}

export function ErrorBanner({
    title,
    message,
    action,
    variant = 'error',
    onDismiss
}: ErrorBannerProps) {
    const styles = {
        error: {
            bg: 'bg-red-600/10',
            border: 'border-red-500/30',
            icon: 'text-red-400',
            title: 'text-red-300',
            message: 'text-red-400/80',
        },
        warning: {
            bg: 'bg-amber-600/10',
            border: 'border-amber-500/30',
            icon: 'text-amber-400',
            title: 'text-amber-300',
            message: 'text-amber-400/80',
        },
    };

    const style = styles[variant];
    const Icon = variant === 'error' ? AlertCircle : AlertTriangle;

    return (
        <div className={`relative p-4 md:p-6 rounded-2xl ${style.bg} border ${style.border} backdrop-blur-sm`}>
            <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`shrink-0 ${style.icon}`}>
                    <Icon size={24} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h4 className={`text-base md:text-lg font-bold ${style.title} mb-2`}>
                        {title}
                    </h4>
                    <p className={`text-sm md:text-base ${style.message} leading-relaxed mb-4`}>
                        {message}
                    </p>

                    {/* Action Button */}
                    {action && (
                        <Button
                            onClick={action.onClick}
                            variant={variant === 'error' ? 'outline' : 'amber'}
                            size="sm"
                        >
                            {action.label}
                        </Button>
                    )}
                </div>

                {/* Dismiss Button */}
                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className={`shrink-0 w-8 h-8 rounded-lg ${style.icon} hover:bg-white/5 transition-colors flex items-center justify-center`}
                        aria-label="Dismiss"
                    >
                        <X size={18} />
                    </button>
                )}
            </div>
        </div>
    );
}
