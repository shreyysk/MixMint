"use client";

import React from "react";
import Link from "next/link";
import { Music, Download, Play, ArrowUpRight } from "lucide-react";
import { cn } from "@/app/lib/utils";

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
  djName,
  djSlug,
  youtubeUrl,
  onDownload,
  isPurchased = false,
  className,
}: TrackCardProps) {
  return (
    <Link
      href={`/track/${id}`}
      className={cn(
        "group relative block overflow-hidden rounded-2xl bg-zinc-900/60 border border-zinc-800/60 hover:border-violet-500/40 transition-all duration-500 hover:shadow-[0_0_40px_rgba(124,58,237,0.15)]",
        className
      )}
      data-testid={`track-card-${id}`}
    >
      {/* Background Gradient on Hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-violet-600/0 via-transparent to-indigo-600/0 group-hover:from-violet-600/5 group-hover:to-indigo-600/5 transition-all duration-500" />
      
      {/* Content */}
      <div className="relative p-6">
        {/* Top Row: Icon + Actions */}
        <div className="flex items-start justify-between mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600/20 to-violet-600/5 border border-violet-500/20 flex items-center justify-center group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
            <Music className="text-violet-400" size={20} />
          </div>
          
          <div className="flex items-center gap-2">
            {youtubeUrl && (
              <div className="w-8 h-8 rounded-lg bg-zinc-800/80 flex items-center justify-center text-zinc-500 group-hover:text-violet-400 transition-colors">
                <Play size={14} />
              </div>
            )}
            {isPurchased && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  onDownload?.(id);
                }}
                className="w-8 h-8 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 hover:bg-emerald-600/30 transition-colors"
                data-testid={`track-download-${id}`}
              >
                <Download size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Track Info */}
        <div className="space-y-2 mb-6">
          <h3 className="text-base font-bold text-white leading-tight line-clamp-2 group-hover:text-violet-100 transition-colors">
            {title}
          </h3>
          
          {djName && djSlug && (
            <p className="text-sm text-zinc-500 font-medium">
              by <span className="text-zinc-400 group-hover:text-violet-300 transition-colors">{djName}</span>
            </p>
          )}
        </div>

        {/* Bottom CTA */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800/50">
          <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            {isPurchased ? "Owned" : "View Details"}
          </span>
          <div className="w-8 h-8 rounded-full bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400 group-hover:bg-violet-600 group-hover:text-white group-hover:scale-110 transition-all duration-300">
            <ArrowUpRight size={14} />
          </div>
        </div>
      </div>
    </Link>
  );
}
