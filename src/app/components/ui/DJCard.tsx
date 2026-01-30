"use client";

import Image from "next/image";
import { Button } from "./Button";
import { User } from "lucide-react";

interface DJCardProps {
    name: string;
    genre: string;
    image: string;
}

export function DJCard({ name, genre, image }: DJCardProps) {
    return (
        <div className="group relative overflow-hidden rounded-2xl bg-zinc-900/50 border border-zinc-800 transition-all hover:border-violet-500/50 shadow-xl">
            <div className="aspect-[4/5] relative overflow-hidden">
                <Image
                    src={image}
                    alt={name}
                    fill
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0B0B0F] via-transparent to-transparent opacity-80" />
            </div>

            <div className="absolute bottom-0 left-0 right-0 p-6">
                <div className="inline-block px-2 py-0.5 rounded bg-violet-600/20 border border-violet-500/30 text-[10px] font-black uppercase tracking-widest text-violet-400 mb-2">
                    {genre}
                </div>
                <h3 className="text-xl font-black text-white uppercase italic tracking-tighter mb-4">{name}</h3>
                <Button variant="outline" size="sm" className="w-full h-9 text-[10px]">View Profile</Button>
            </div>
        </div>
    );
}
