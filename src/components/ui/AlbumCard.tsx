
"use client";

import React from "react";
import Link from "next/link";
import { Package, Download, Check, Play, Disc3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface AlbumCardProps {
    id: string;
    title: string;
    description?: string | null;
    price?: number;
    fileSize?: number;
    djName?: string;
    djSlug?: string;
    trackCount?: number;
    coverUrl?: string;
    isPurchased?: boolean;
    onPurchase?: (albumId: string) => void;
    onDownload?: (albumId: string) => void;
    className?: string;
}

export function AlbumCard({
    id,
    title,
    description,
    price,
    fileSize,
    djName,
    djSlug,
    trackCount,
    coverUrl,
    isPurchased = false,
    onPurchase,
    onDownload,
    className,
}: AlbumCardProps) {

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

    return (
        <div
            className={cn(
                "group relative bg-surface-dark rounded-2xl overflow-hidden h-full flex flex-col transition-all duration-300",
                "hover:shadow-purple-glow-lg hover:-translate-y-1",
                isPurchased && "card-owned",
                className
            )}
            data-testid={`album-card-${id}`}
        >
            {/* Cover Art */}
            <div className="relative aspect-square overflow-hidden">
                {coverUrl ? (
                    <img
                        src={coverUrl}
                        alt={title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-purple">
                        <Disc3 size={64} className="text-white/30" />
                    </div>
                )}

                {/* Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />

                {/* Play Button */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button className="w-12 h-12 rounded-full bg-purple-primary flex items-center justify-center shadow-purple-glow hover:scale-110 transition-transform">
                        <Play size={20} fill="white" className="text-white ml-0.5" />
                    </button>
                </div>

                {/* Badges */}
                <div className="absolute top-3 left-3 flex gap-2">
                    {isPurchased && (
                        <span className="badge-owned">
                            <Check size={10} /> Owned
                        </span>
                    )}
                    {trackCount && (
                        <span className="bg-black/50 backdrop-blur-sm text-white text-[10px] px-2 py-1 rounded-full font-medium">
                            {trackCount} tracks
                        </span>
                    )}
                </div>
            </div>

            {/* Content */}
            <Link href={`/album/${id}`} className="block p-4 flex-grow">
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

                {description && (
                    <p className="text-xs text-zinc-600 line-clamp-2 mb-2">
                        {description}
                    </p>
                )}

                {fileSize && (
                    <p className="text-[10px] text-zinc-600">
                        {(fileSize / 1024 / 1024).toFixed(1)} MB
                    </p>
                )}
            </Link>

            {/* Footer */}
            <div className="px-4 pb-4 mt-auto">
                <div className="flex items-center justify-between pt-3 border-t border-white/5">
                    <span className="price text-lg text-white">
                        {price !== undefined && price > 0 ? `₹${price}` : 'FREE'}
                    </span>

                    {isPurchased ? (
                        <Button
                            onClick={handleDownload}
                            size="sm"
                            className="btn-mint !py-1.5 !px-3 flex items-center gap-1.5"
                        >
                            <Download size={14} />
                            Download
                        </Button>
                    ) : (
                        <Button
                            onClick={handlePurchase}
                            size="sm"
                            className="btn-primary !py-1.5 !px-3"
                        >
                            {price === 0 ? 'Get Free' : 'Buy Album'}
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
}
