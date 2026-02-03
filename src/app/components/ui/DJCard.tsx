"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

interface DJCardProps {
    name: string;
    slug: string;
    genre: string[];
    image: string;
}

export function DJCard({ name, slug, genre, image }: DJCardProps) {
    return (
        <Link 
            href={`/dj/${slug}`}
            className="group relative block overflow-hidden rounded-2xl bg-zinc-900/60 border border-zinc-800/60 hover:border-violet-500/40 transition-all duration-500 hover:shadow-[0_0_50px_rgba(124,58,237,0.12)]"
        >
            {/* Image Container */}
            <div className="aspect-[4/5] relative overflow-hidden">
                <Image
                    src={image}
                    alt={name}
                    fill
                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                />
                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/60 to-transparent" />
                
                {/* Hover Glow */}
                <div className="absolute inset-0 bg-gradient-to-t from-violet-600/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </div>

            {/* Content Overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
                {/* Genre Tags */}
                {genre.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                        {genre.slice(0, 2).map(g => (
                            <span 
                                key={g} 
                                className="px-2 py-0.5 rounded-md bg-violet-600/20 border border-violet-500/30 text-[10px] font-semibold uppercase tracking-wide text-violet-300"
                            >
                                {g}
                            </span>
                        ))}
                    </div>
                )}

                {/* DJ Name + CTA Row */}
                <div className="flex items-end justify-between gap-4">
                    <h3 className="text-xl font-bold text-white leading-tight group-hover:text-violet-100 transition-colors">
                        {name}
                    </h3>
                    <div className="shrink-0 w-10 h-10 rounded-full bg-violet-600/10 border border-violet-500/30 flex items-center justify-center text-violet-400 group-hover:bg-violet-600 group-hover:text-white group-hover:scale-110 transition-all duration-300">
                        <ArrowUpRight size={18} />
                    </div>
                </div>
            </div>
        </Link>
    );
}
