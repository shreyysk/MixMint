import React from "react";
import Link from "next/link";
import { Music, Download, Check, Lock, Play, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface TrackCardProps {
    id: string;
    title: string;
    price?: number;
    djName?: string;
    djSlug?: string;
    bpm?: number;
    genre?: string;
    coverUrl?: string;
    onDownload?: (trackId: string) => void;
    onPurchase?: (trackId: string) => void;
    isPurchased?: boolean;
    isFanOnly?: boolean;
    userTier?: string;
    isNew?: boolean;
    className?: string;
}

export function TrackCard({
    id,
    title,
    price,
    djName,
    djSlug,
    bpm,
    genre,
    coverUrl,
    onDownload,
    onPurchase,
    isPurchased = false,
    isFanOnly = false,
    userTier,
    isNew = false,
    className,
}: TrackCardProps) {

    const handlePurchase = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (onPurchase) {
            onPurchase(id);
        }
    }

    const handleDownload = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (onDownload) {
            onDownload(id);
        }
    }

    const isLocked = isFanOnly && userTier !== 'super';

    // Card state classes
    const cardStateClass = isPurchased
        ? "card-owned"
        : isLocked
            ? "card-locked"
            : "card-available";

    return (
        <div
            className={cn(
                "group relative bg-surface-dark rounded-2xl overflow-hidden h-full flex flex-col transition-all duration-300",
                "hover:shadow-purple-glow-lg hover:-translate-y-1",
                cardStateClass,
                className
            )}
            data-testid={`track-card-${id}`}
        >
            {/* Cover Art */}
            <div className="relative aspect-square bg-zinc-800 overflow-hidden">
                {coverUrl ? (
                    <img
                        src={coverUrl}
                        alt={title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-purple">
                        <Music size={48} className="text-white/30" />
                    </div>
                )}

                {/* Play Button Overlay */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button className="w-14 h-14 rounded-full bg-purple-primary flex items-center justify-center shadow-purple-glow hover:scale-110 transition-transform">
                        <Play size={24} fill="white" className="text-white ml-1" />
                    </button>
                </div>

                {/* Badges */}
                <div className="absolute top-3 left-3 flex gap-2">
                    {isNew && <span className="badge-new">NEW</span>}
                    {isPurchased && <span className="badge-owned"><Check size={10} /> Owned</span>}
                    {isFanOnly && <span className="badge-super"><Sparkles size={10} /> Super</span>}
                </div>

                {/* Lock Overlay */}
                {isLocked && (
                    <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                        <Lock size={32} className="text-gold" />
                    </div>
                )}
            </div>

            {/* Content */}
            <Link href={isLocked ? "#" : `/track/${id}`} className="block p-4 flex-grow">
                <h3 className="font-heading font-bold text-white text-sm line-clamp-2 mb-1 group-hover:text-purple-primary-dark transition-colors">
                    {title}
                </h3>

                {djName && (
                    <p className="text-xs text-zinc-500 mb-2 truncate">
                        {djSlug ? (
                            <Link
                                href={`/dj/${djSlug}`}
                                className="hover:text-mint-accent transition-colors"
                                onClick={(e) => e.stopPropagation()}
                            >
                                {djName}
                            </Link>
                        ) : djName}
                    </p>
                )}

                {/* Meta */}
                <div className="flex items-center gap-3 text-xs text-zinc-500">
                    {bpm && <span>{bpm} BPM</span>}
                    {genre && <span className="bg-zinc-800 px-2 py-0.5 rounded">{genre}</span>}
                </div>
            </Link>

            {/* Footer */}
            <div className="px-4 pb-4 mt-auto">
                <div className="flex items-center justify-between pt-3 border-t border-white/5">
                    {price !== undefined && (
                        <span className="price text-lg text-white">
                            {price === 0 ? 'FREE' : `₹${price}`}
                        </span>
                    )}

                    {isPurchased ? (
                        <Button
                            onClick={handleDownload}
                            size="sm"
                            className="btn-mint !py-1.5 !px-3 flex items-center gap-1.5"
                        >
                            <Download size={14} />
                            Download
                        </Button>
                    ) : isLocked ? (
                        <Button
                            size="sm"
                            className="bg-gradient-super text-white !py-1.5 !px-3"
                            onClick={handlePurchase}
                        >
                            Upgrade
                        </Button>
                    ) : (
                        <Button
                            onClick={handlePurchase}
                            size="sm"
                            className="btn-primary !py-1.5 !px-3"
                        >
                            {price === 0 ? 'Get Free' : 'Buy Now'}
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
}
