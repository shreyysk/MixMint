
"use client";

import React from "react";
import Link from "next/link";
import { Music, Download, Play, ArrowUpRight } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "./Button";

interface TrackCardProps {
    id: string;
    title: string;
    price?: number;
    djName?: string;
    djSlug?: string;
    youtube_url?: string | null;
    onDownload?: (trackId: string) => void;
    onPurchase?: (trackId: string) => void;
    isPurchased?: boolean;
    className?: string;
}

export function TrackCard({
    id,
    title,
    price,
    djName,
    djSlug,
    youtube_url,
    onDownload,
    onPurchase,
    isPurchased = false,
    className,
}: TrackCardProps) {

    const handlePurchase = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (onPurchase) {
            onPurchase(id);
        }
    }

    return (
        <div 
            className={cn("group bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden h-full flex flex-col transition-all duration-300 hover:border-violet-500/50 hover:shadow-lg hover:shadow-violet-500/10 hover:-translate-y-1", className)}
            data-testid={`track-card-${id}`}
        >
            <Link href={`/track/${id}`} className="block p-4 flex-grow">
                <div className="flex justify-between items-start">
                    <h3 className="text-lg font-bold text-white mb-2 line-clamp-2 leading-snug">
                        {title}
                    </h3>
                    <Music className="h-5 w-5 text-zinc-500 flex-shrink-0" />
                </div>
                
                {djName && djSlug && (
                     <Link href={`/djs/${djSlug}`} className="text-sm text-zinc-400 hover:text-violet-400 transition-colors line-clamp-1">
                        by {djName}
                    </Link>
                )}
            </Link>

            <div className="px-4 pb-4 mt-auto">
                 <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60">
                    {price !== undefined && (
                        <span className="text-xl font-bold text-white">
                            ${price.toFixed(2)}
                        </span>
                    )}
                    
                    <Button 
                        onClick={handlePurchase}
                        size="sm"
                    >
                        Purchase
                    </Button>
                </div>
            </div>
        </div>
    );
}
