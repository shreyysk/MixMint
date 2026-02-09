'use client';

import Image from 'next/image';
import Link from 'next/link';
import { ArrowUpRight, Music2, BadgeCheck, Headphones } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DJCardProps {
  name: string;
  slug: string;
  genre: string[];
  image: string | null;
  isVerified?: boolean;
  subscriberCount?: number;
  trackCount?: number;
  className?: string;
}

export function DJCard({
  name,
  slug,
  genre,
  image,
  isVerified = false,
  subscriberCount,
  trackCount,
  className
}: DJCardProps) {
  return (
    <Link
      href={`/dj/${slug}`}
      className={cn(
        "group block rounded-2xl overflow-hidden bg-surface-dark h-full transition-all duration-300",
        "hover:shadow-purple-glow-lg hover:-translate-y-1",
        className
      )}
    >
      {/* Cover/Avatar Area */}
      <div className="relative aspect-square w-full overflow-hidden">
        {image ? (
          <Image
            src={image}
            alt={name}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full bg-gradient-purple flex items-center justify-center">
            <Music2 className="text-white/30" size={64} />
          </div>
        )}

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* Avatar glow effect on hover */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-purple-primary/30 to-transparent" />
        </div>

        {/* Verified badge */}
        {isVerified && (
          <div className="absolute top-3 right-3 bg-purple-primary/90 p-1.5 rounded-full shadow-purple-glow">
            <BadgeCheck size={14} className="text-white" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-heading font-bold text-white text-base mb-2 truncate group-hover:text-purple-primary-dark transition-colors">
          {name}
        </h3>

        {/* Genre tags */}
        {genre?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {genre.slice(0, 2).map(g => (
              <span
                key={g}
                className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/5 text-zinc-400 border border-white/5"
              >
                {g}
              </span>
            ))}
          </div>
        )}

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-zinc-500 mb-3">
          {subscriberCount !== undefined && (
            <span>{subscriberCount.toLocaleString()} fans</span>
          )}
          {trackCount !== undefined && (
            <span className="flex items-center gap-1">
              <Headphones size={12} /> {trackCount} tracks
            </span>
          )}
        </div>

        {/* CTA */}
        <div className="flex items-center justify-between text-sm text-zinc-400 group-hover:text-mint-accent transition-colors">
          <span className="font-medium">View Profile</span>
          <ArrowUpRight className="h-4 w-4 transform transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </div>
      </div>
    </Link>
  );
}
