"use client";

import React from "react";
import Link from "next/link";
import { Music, Download, Play } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "./Button";

interface TrackCardProps {
  id: string;
  title: string;
  price: number;
  djName?: string;
  djSlug?: string;
  youtubeUrl?: string | null;
  onDownload?: (trackId: string) => void;
  isPurchased?: boolean;
  className?: string;
}

export function TrackCard({
  id,
  title,
  price,
  djName,
  djSlug,
  youtubeUrl,
  onDownload,
  isPurchased = false,
  className,
}: TrackCardProps) {
  return (
    <div
      className={cn(
        "group relative p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-violet-500/30 transition-all duration-300",
        className
      )}
      data-testid={`track-card-${id}`}
    >
      {/* Icon Badge */}
      <div className="w-14 h-14 rounded-xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <Music className="text-violet-500" size={24} />
      </div>

      {/* Track Info */}
      <div className="mb-4">
        <h3 className="text-lg font-black text-white uppercase tracking-tight mb-2 line-clamp-1">
          {title}
        </h3>
        
        {djName && djSlug && (
          <Link 
            href={`/dj/${djSlug}`}
            className="text-sm text-zinc-500 hover:text-violet-400 transition-colors font-bold"
          >
            by {djName}
          </Link>
        )}
      </div>

      {/* Price & Actions */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <span className="text-2xl font-black text-white italic">₹{price}</span>
          <span className="text-[10px] text-zinc-600 font-black uppercase tracking-wider">per track</span>
        </div>

        <div className="flex items-center gap-2">
          {youtubeUrl && (
            <Link href={`/track/${id}`}>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                data-testid={`track-preview-${id}`}
              >
                <Play size={14} />
                Preview
              </Button>
            </Link>
          )}

          {isPurchased ? (
            <Button
              size="sm"
              onClick={() => onDownload?.(id)}
              className="gap-2 bg-green-600 hover:bg-green-700"
              data-testid={`track-download-${id}`}
            >
              <Download size={14} />
              Download
            </Button>
          ) : (
            <Link href={`/track/${id}`}>
              <Button
                size="sm"
                className="gap-2"
                data-testid={`track-buy-${id}`}
              >
                Buy Now
              </Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
