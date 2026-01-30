"use client";

import React from "react";
import { MOCK_DJS } from "@/app/lib/mock-djs";
import { DJCard } from "@/app/components/ui/DJCard";
import { Search, Filter } from "lucide-react";

export default function ExplorePage() {
    return (
        <div className="pb-24">
            <div className="px-6 md:px-12">
                <div className="max-w-7xl mx-auto">
                    {/* Header */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-16">
                        <div>
                            <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4">
                                Explore <span className="text-violet-gradient">DJs</span>
                            </h1>
                            <p className="text-zinc-500 font-bold max-w-lg">
                                Discover the architects of the soundscape. 12 legends pushing the boundaries of audio.
                            </p>
                        </div>

                        {/* Mock Search/Filter UI */}
                        <div className="flex items-center gap-3">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-violet-500 transition-colors" size={18} />
                                <input
                                    type="text"
                                    placeholder="Search genres, names..."
                                    className="bg-zinc-900 border border-zinc-800 rounded-xl pl-12 pr-4 py-3 text-sm focus:outline-none focus:border-violet-500/50 w-full md:w-64 transition-all"
                                />
                            </div>
                            <button className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-400 hover:text-white hover:border-violet-500/30 transition-all shrink-0">
                                <Filter size={20} />
                            </button>
                        </div>
                    </div>

                    {/* Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                        {MOCK_DJS.map((dj) => (
                            <DJCard
                                key={dj.id}
                                name={dj.name}
                                slug={dj.slug}
                                genre={dj.genre}
                                image={dj.image}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
