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
        "group relative block overflow-hidden rounded-2xl bg-zinc-900/60 border border-zinc-800/60 hover:border-amber-500/40 transition-all duration-500 hover:shadow-[0_0_40px_rgba(245,158,11,0.12)]",
        className
      )}
      data-testid={`album-card-${id}`}
    >
      {/* Background Gradient on Hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/0 via-transparent to-orange-600/0 group-hover:from-amber-600/5 group-hover:to-orange-600/5 transition-all duration-500" />
      
      {/* Content */}
      <div className="relative p-6">
        {/* Top Row: Icon + Download */}
        <div className="flex items-start justify-between mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-600/20 to-amber-600/5 border border-amber-500/20 flex items-center justify-center group-hover:scale-110 group-hover:rotate-3 transition-all duration-300">
            <FileArchive className="text-amber-400" size={20} />
          </div>
          
          {isPurchased && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onDownload?.(id);
              }}
              className="w-8 h-8 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 hover:bg-emerald-600/30 transition-colors"
              data-testid={`album-download-${id}`}
            >
              <Download size={14} />
            </button>
          )}
        </div>

        {/* Album Info */}
        <div className="space-y-2 mb-4">
          <h3 className="text-base font-bold text-white leading-tight line-clamp-2 group-hover:text-amber-100 transition-colors">
            {title}
          </h3>
          
          {djName && djSlug && (
            <p className="text-sm text-zinc-500 font-medium">
              by <span className="text-zinc-400 group-hover:text-amber-300 transition-colors">{djName}</span>
            </p>
          )}

          {description && (
            <p className="text-sm text-zinc-600 line-clamp-2 leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {/* File Info Badge */}
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-800/60 text-xs text-zinc-400 font-medium mb-4">
          <Package size={12} />
          <span>ZIP • {formatFileSize(fileSize)}</span>
        </div>

        {/* Bottom CTA */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800/50">
          <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            {isPurchased ? "Owned" : "View Pack"}
          </span>
          <div className="w-8 h-8 rounded-full bg-amber-600/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:bg-amber-600 group-hover:text-white group-hover:scale-110 transition-all duration-300">
            <ArrowUpRight size={14} />
          </div>
        </div>
      </div>
    </Link>
  );
}
