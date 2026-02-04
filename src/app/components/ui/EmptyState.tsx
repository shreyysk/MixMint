import React from "react";
import Link from "next/link";
import { Button } from "./Button";

interface EmptyStateProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    action?: {
        label: string;
        href?: string;
        onClick?: () => void;
    };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-20 md:py-32 px-6">
            {/* Icon Container */}
            <div className="w-20 h-20 md:w-24 md:h-24 rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 flex items-center justify-center mb-6 text-zinc-600">
                {icon}
            </div>

            {/* Content */}
            <div className="text-center max-w-md">
                <h3 className="text-xl md:text-2xl font-bold text-white mb-3">
                    {title}
                </h3>
                <p className="text-sm md:text-base text-zinc-500 leading-relaxed mb-6">
                    {description}
                </p>

                {/* Action Button */}
                {action && (
                    <>
                        {action.href ? (
                            <Link href={action.href}>
                                <Button variant="primary" size="lg">
                                    {action.label}
                                </Button>
                            </Link>
                        ) : (
                            <Button variant="primary" size="lg" onClick={action.onClick}>
                                {action.label}
                            </Button>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
