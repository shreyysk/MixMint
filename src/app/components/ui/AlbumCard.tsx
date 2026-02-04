"use client";

import React from "react";
import Link from "next/link";
import { Package, Download, FileArchive, ArrowUpRight } from "lucide-react";
import { cn } from "@/app/lib/utils";

interface AlbumCardProps {
  id: string;
  title: string;
  description?: string | null;
  price: number;
  fileSize: number;
  djName?: string;
  djSlug?: string;
  onDownload?: (albumId: string) => void;
  isPurchased?: boolean;
  className?: string;
}

export function AlbumCard({
  id,
  title,
  description,
  fileSize,
  djName,
  djSlug,
  onDownload,
  isPurchased = false,
  className,
}: AlbumCardProps) {
  // Format file size
  const formatFileSize = (bytes: number) => {
    if (!bytes) return "—";
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(1) + " MB";
  };

  return (
    <Link
      href={`/album/${id}`}
      className={cn(
        "group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 hover:border-amber-500/50 transition-all duration-500 hover:shadow-[0_8px_60px_rgba(245,158,11,0.2)] hover:-translate-y-1",
        className
      )}
      data-testid={`album-card-${id}`}
    >
      {/* Background Gradient on Hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/0 via-transparent to-orange-600/0 group-hover:from-amber-600/8 group-hover:to-orange-600/8 transition-all duration-500" />

      {/* Shine Effect */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
      </div>

      {/* Content */}
      <div className="relative p-6">
        {/* Top Row: Icon + Download */}
        <div className="flex items-start justify-between mb-6">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-amber-600/25 to-amber-600/5 border border-amber-500/30 flex items-center justify-center group-hover:scale-110 group-hover:rotate-6 transition-all duration-500 shadow-lg shadow-amber-500/10">
            <FileArchive className="text-amber-400 group-hover:text-amber-300 transition-colors duration-300" size={22} />
          </div>

          {isPurchased && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onDownload?.(id);
              }}
              className="w-9 h-9 rounded-lg bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 hover:bg-emerald-600/30 hover:scale-110 transition-all duration-300 shadow-lg shadow-emerald-500/10"
              data-testid={`album-download-${id}`}
            >
              <Download size={16} />
            </button>
          )}
        </div>

        {/* Album Info */}
        <div className="space-y-2.5 mb-5">
          <h3 className="text-lg font-extrabold text-white leading-tight line-clamp-2 group-hover:text-amber-50 transition-colors duration-300">
            {title}
          </h3>

          {djName && djSlug && (
            <p className="text-sm text-zinc-500 font-semibold">
              by <span className="text-zinc-400 group-hover:text-amber-300 transition-colors duration-300">{djName}</span>
            </p>
          )}

          {description && (
            <p className="text-sm text-zinc-500 line-clamp-2 leading-relaxed group-hover:text-zinc-400 transition-colors duration-300">
              {description}
            </p>
          )}
        </div>

        {/* File Info Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-br from-zinc-800/80 to-zinc-800/40 border border-zinc-700/50 text-xs text-zinc-300 font-bold mb-5 group-hover:border-amber-500/30 group-hover:from-amber-600/10 group-hover:to-amber-600/5 transition-all duration-300 shadow-sm">
          <Package size={14} className="text-zinc-400 group-hover:text-amber-400 transition-colors duration-300" />
          <span className="uppercase tracking-wide">ZIP • {formatFileSize(fileSize)}</span>
        </div>

        {/* Bottom CTA */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60 group-hover:border-zinc-700/60 transition-colors duration-300">
          <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest group-hover:text-zinc-400 transition-colors duration-300">
            {isPurchased ? "Owned" : "View Pack"}
          </span>
          <div className="w-9 h-9 rounded-full bg-amber-600/10 border border-amber-500/30 flex items-center justify-center text-amber-400 group-hover:bg-amber-600 group-hover:text-white group-hover:scale-125 group-hover:rotate-12 transition-all duration-500 shadow-lg shadow-amber-500/0 group-hover:shadow-amber-500/50">
            <ArrowUpRight size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-300" />
          </div>
        </div>
      </div>
    </Link>
  );
}
