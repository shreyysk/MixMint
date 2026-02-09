'use client';

import Image from 'next/image';
import Link from 'next/link';
import { ArrowUpRight, Music2 } from 'lucide-react';

interface DJCardProps {
  name: string;
  slug: string;
  genre: string[];
  image: string | null;
}

export function DJCard({ name, slug, genre, image }: DJCardProps) {
  return (
    <Link
      href={`/dj/${slug}`}
      className="group block rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 h-full transition-all duration-300 hover:border-violet-500/50 hover:shadow-lg hover:shadow-violet-500/10 hover:-translate-y-1"
    >
      <div className="relative aspect-[4/5] w-full overflow-hidden">
        {image ? (
          <Image
            src={image}
            alt={name}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full bg-zinc-800 flex items-center justify-center">
            <Music2 className="text-zinc-600" size={48} />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
      </div>

      <div className="p-4">
        <h3 className="text-lg font-bold text-white mb-2 truncate">{name}</h3>
        {genre?.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {genre.slice(0, 2).map(g => (
              <span
                key={g}
                className="px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-300"
              >
                {g}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between text-sm text-zinc-400 group-hover:text-violet-300 transition-colors">
          <span>View Profile</span>
          <ArrowUpRight className="h-4 w-4 transform transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </div>
      </div>
    </Link>
  );
}
