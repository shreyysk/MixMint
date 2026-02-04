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
        "group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 hover:border-violet-500/50 transition-all duration-500 hover:shadow-[0_8px_60px_rgba(124,58,237,0.25)] hover:-translate-y-1",
        className
      )}
      data-testid={`track-card-${id}`}
    >
      {/* Background Gradient on Hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-violet-600/0 via-transparent to-indigo-600/0 group-hover:from-violet-600/8 group-hover:to-indigo-600/8 transition-all duration-500" />

      {/* Shine Effect */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
      </div>

      {/* Content */}
      <div className="relative p-6">
        {/* Top Row: Icon + Actions */}
        <div className="flex items-start justify-between mb-6">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-600/25 to-violet-600/5 border border-violet-500/30 flex items-center justify-center group-hover:scale-110 group-hover:rotate-6 transition-all duration-500 shadow-lg shadow-violet-500/10">
            <Music className="text-violet-400 group-hover:text-violet-300 transition-colors duration-300" size={22} />
          </div>

          <div className="flex items-center gap-2">
            {youtubeUrl && (
              <div className="w-9 h-9 rounded-lg bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center text-zinc-500 group-hover:text-violet-400 group-hover:border-violet-500/30 group-hover:bg-zinc-800 transition-all duration-300">
                <Play size={16} />
              </div>
            )}
            {isPurchased && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  onDownload?.(id);
                }}
                className="w-9 h-9 rounded-lg bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 hover:bg-emerald-600/30 hover:scale-110 transition-all duration-300 shadow-lg shadow-emerald-500/10"
                data-testid={`track-download-${id}`}
              >
                <Download size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Track Info */}
        <div className="space-y-2 mb-6">
          <h3 className="text-lg font-extrabold text-white leading-tight line-clamp-2 group-hover:text-violet-50 transition-colors duration-300">
            {title}
          </h3>

          {djName && djSlug && (
            <p className="text-sm text-zinc-500 font-semibold">
              by <span className="text-zinc-400 group-hover:text-violet-300 transition-colors duration-300">{djName}</span>
            </p>
          )}
        </div>

        {/* Bottom CTA */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60 group-hover:border-zinc-700/60 transition-colors duration-300">
          <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest group-hover:text-zinc-400 transition-colors duration-300">
            {isPurchased ? "Owned" : "View Details"}
          </span>
          <div className="w-9 h-9 rounded-full bg-violet-600/10 border border-violet-500/30 flex items-center justify-center text-violet-400 group-hover:bg-violet-600 group-hover:text-white group-hover:scale-125 group-hover:rotate-12 transition-all duration-500 shadow-lg shadow-violet-500/0 group-hover:shadow-violet-500/50">
            <ArrowUpRight size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-300" />
          </div>
        </div>
      </div>
    </Link>
  );
}
