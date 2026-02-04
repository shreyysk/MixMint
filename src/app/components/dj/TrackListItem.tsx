"use client";

import React from "react";
import { Music, Edit, Trash2, Calendar, DollarSign } from "lucide-react";
import { Button } from "@/app/components/ui/Button";

interface TrackListItemProps {
    id: string;
    title: string;
    price: number;
    createdAt: string;
    purchaseCount?: number;
    onEdit: (id: string) => void;
    onDelete: (id: string) => void;
}

export function TrackListItem({
    id,
    title,
    price,
    createdAt,
    purchaseCount = 0,
    onEdit,
    onDelete,
}: TrackListItemProps) {
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    return (
        <div className="group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 hover:border-violet-500/40 transition-all duration-300 p-6">
            <div className="flex items-start justify-between gap-4">
                {/* Icon */}
                <div className="w-12 h-12 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shrink-0">
                    <Music className="text-violet-400" size={20} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-bold text-white mb-2 line-clamp-1">
                        {title}
                    </h3>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500 mb-3">
                        <span className="inline-flex items-center gap-1.5">
                            <Calendar size={12} />
                            {formatDate(createdAt)}
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                            <DollarSign size={12} />
                            {price === 0 ? 'Free' : `₹${price}`}
                        </span>
                        {purchaseCount > 0 && (
                            <span className="px-2 py-0.5 rounded bg-emerald-600/20 border border-emerald-500/40 text-emerald-400 font-bold">
                                {purchaseCount} {purchaseCount === 1 ? 'sale' : 'sales'}
                            </span>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                        <Button
                            onClick={() => onEdit(id)}
                            variant="outline"
                            size="sm"
                        >
                            <Edit size={14} />
                            Edit
                        </Button>
                        <Button
                            onClick={() => onDelete(id)}
                            variant="outline"
                            size="sm"
                            className="text-red-400 hover:text-red-300 border-red-500/40 hover:border-red-500/60"
                        >
                            <Trash2 size={14} />
                            Delete
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
