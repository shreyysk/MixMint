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
            className="group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 hover:border-violet-500/50 transition-all duration-500 hover:shadow-[0_8px_60px_rgba(124,58,237,0.2)] hover:-translate-y-1"
        >
            {/* Image Container */}
            <div className="aspect-[4/5] relative overflow-hidden">
                <Image
                    src={image}
                    alt={name}
                    fill
                    className="object-cover transition-transform duration-700 group-hover:scale-110"
                />
                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/70 to-transparent" />

                {/* Hover Glow */}
                <div className="absolute inset-0 bg-gradient-to-t from-violet-600/20 via-violet-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                {/* Shine Effect */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                </div>
            </div>

            {/* Content Overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
                {/* Genre Tags */}
                {genre.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {genre.slice(0, 2).map(g => (
                            <span
                                key={g}
                                className="px-2.5 py-1 rounded-lg bg-violet-600/25 backdrop-blur-sm border border-violet-500/40 text-[11px] font-bold uppercase tracking-wider text-violet-200 shadow-lg shadow-violet-500/10 group-hover:bg-violet-600/35 group-hover:border-violet-500/50 transition-all duration-300"
                            >
                                {g}
                            </span>
                        ))}
                    </div>
                )}

                {/* DJ Name + CTA Row */}
                <div className="flex items-end justify-between gap-4">
                    <h3 className="text-xl font-extrabold text-white leading-tight group-hover:text-violet-50 transition-colors duration-300">
                        {name}
                    </h3>
                    <div className="shrink-0 w-11 h-11 rounded-full bg-violet-600/10 border border-violet-500/40 flex items-center justify-center text-violet-400 group-hover:bg-violet-600 group-hover:text-white group-hover:scale-125 group-hover:rotate-12 transition-all duration-500 shadow-lg shadow-violet-500/0 group-hover:shadow-violet-500/50">
                        <ArrowUpRight size={20} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-300" />
                    </div>
                </div>
            </div>
        </Link>
    );
}
