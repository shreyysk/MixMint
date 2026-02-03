"use client";

import React from "react";
import Link from "next/link";
import { Package, Download, FileArchive } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "./Button";

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
  price,
  fileSize,
  djName,
  djSlug,
  onDownload,
  isPurchased = false,
  className,
}: AlbumCardProps) {
  // Format file size
  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(2) + " MB";
  };

  return (
    <div
      className={cn(
        "group relative p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-amber-500/30 transition-all duration-300",
        className
      )}
      data-testid={`album-card-${id}`}
    >
      {/* ZIP Badge */}
      <div className="w-14 h-14 rounded-xl bg-amber-600/10 border border-amber-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <FileArchive className="text-amber-500" size={24} />
      </div>

      {/* Album Info */}
      <div className="mb-4">
        <h3 className="text-lg font-black text-white uppercase tracking-tight mb-2 line-clamp-1">
          {title}
        </h3>
        
        {djName && djSlug && (
          <Link 
            href={`/dj/${djSlug}`}
            className="text-sm text-zinc-500 hover:text-amber-400 transition-colors font-bold mb-2 block"
          >
            by {djName}
          </Link>
        )}

        {description && (
          <p className="text-sm text-zinc-600 line-clamp-2 mb-3">
            {description}
          </p>
        )}

        <div className="flex items-center gap-2 text-xs text-zinc-600 font-bold">
          <Package size={12} />
          <span>{formatFileSize(fileSize)}</span>
        </div>
      </div>

      {/* Price & Actions */}
      <div className="flex items-center justify-between gap-3 pt-4 border-t border-zinc-800/50">
        <div className="flex flex-col">
          <span className="text-2xl font-black text-white italic">₹{price}</span>
          <span className="text-[10px] text-zinc-600 font-black uppercase tracking-wider">album pack</span>
        </div>

        {isPurchased ? (
          <Button
            size="sm"
            onClick={() => onDownload?.(id)}
            className="gap-2 bg-green-600 hover:bg-green-700"
            data-testid={`album-download-${id}`}
          >
            <Download size={14} />
            Download ZIP
          </Button>
        ) : (
          <Link href={`/album/${id}`}>
            <Button
              size="sm"
              className="gap-2 bg-amber-600 hover:bg-amber-700"
              data-testid={`album-buy-${id}`}
            >
              Buy Pack
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
