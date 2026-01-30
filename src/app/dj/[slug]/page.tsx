"use client";

import React, { useState, use } from "react";
import Image from "next/image";
import Link from "next/link";
import { MOCK_DJS } from "@/app/lib/mock-djs";
import { Button } from "@/app/components/ui/Button";
import { Footer } from "@/app/components/Footer";
import {
    Lock,
    Unlock,
    Zap,
    Crown,
    Check,
    Music,
    Package,
    Share2,
    ChevronRight,
    TrendingUp,
    AlertCircle
} from "lucide-react";
import { cn } from "@/app/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export default function DJProfilePage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = use(params);
    const dj = MOCK_DJS.find((d) => d.slug === slug) || MOCK_DJS[0];
    const [activeTab, setActiveTab] = useState<"tracks" | "albums" | "uploads">("tracks");

    const plans = [
        { name: "Basic", price: "₹99", icon: Zap, color: "text-zinc-400", bg: "bg-zinc-900/50", quota: "3 HQ Downloads/mo" },
        { name: "Pro", price: "₹199", icon: TrendingUp, color: "text-violet-400", bg: "bg-violet-900/10", border: "border-violet-500/30", quota: "10 HQ Downloads + Early Access" },
        { name: "Super", price: "₹399", icon: Crown, color: "text-amber-400", bg: "bg-amber-900/10", border: "border-amber-500/30", quota: "Unlimited + Fan Uploads" },
    ];

    return (
        <div className="min-h-screen flex flex-col bg-[#0B0B0F]">
            <main className="flex-grow pt-24 pb-24">
                {/* Banner Section */}
                <section className="relative h-[300px] md:h-[400px] overflow-hidden">
                    {dj.banner ? (
                        <Image src={dj.banner} alt={dj.name} fill className="object-cover" />
                    ) : (
                        <div className="w-full h-full bg-gradient-to-br from-zinc-900 to-black" />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0B0B0F] via-[#0B0B0F]/20 to-transparent" />
                </section>

                <div className="max-w-7xl mx-auto px-6 md:px-12 -mt-32 relative z-10">
                    {/* Header Info */}
                    <div className="flex flex-col md:flex-row items-end gap-8 mb-16">
                        <div className="relative w-48 h-48 rounded-3xl overflow-hidden border-4 border-[#0B0B0F] shadow-2xl shrink-0 bg-zinc-900">
                            <Image src={dj.image} alt={dj.name} fill className="object-cover" />
                        </div>

                        <div className="flex-grow pb-4">
                            <div className="flex flex-wrap gap-2 mb-4">
                                {dj.genre.map(g => (
                                    <span key={g} className="px-2 py-1 rounded-lg bg-violet-600/10 border border-violet-500/20 text-[10px] font-black tracking-widest text-violet-400 uppercase">{g}</span>
                                ))}
                            </div>
                            <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-4 leading-none">{dj.name}</h1>
                            <p className="text-zinc-500 font-bold text-lg max-w-2xl">{dj.bio}</p>
                        </div>

                        <div className="pb-4 flex gap-3">
                            <Button className="h-12 px-8">Follow</Button>
                            <Button variant="outline" className="h-12 w-12 p-0 flex items-center justify-center">
                                <Share2 size={20} />
                            </Button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                        {/* Left Rail: Main Content Storefront */}
                        <div className="lg:col-span-2 space-y-12">
                            {/* Tabs */}
                            <div className="flex border-b border-zinc-900">
                                {(["tracks", "albums", "uploads"] as const).map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={cn(
                                            "px-8 py-4 text-xs font-black uppercase tracking-widest transition-all relative",
                                            activeTab === tab ? "text-white" : "text-zinc-600 hover:text-zinc-400"
                                        )}
                                    >
                                        {tab.replace("-", " ")}
                                        {activeTab === tab && (
                                            <motion.div layoutId="tab-underline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-violet-600" />
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Content */}
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={activeTab}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    {activeTab === "tracks" && (
                                        <div className="space-y-4">
                                            {dj.tracks.length > 0 ? dj.tracks.map((track) => (
                                                <div key={track.id} className="p-4 rounded-2xl bg-zinc-900/30 border border-zinc-800 flex items-center justify-between group hover:border-zinc-700 transition-colors">
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center">
                                                            <Music size={18} className="text-zinc-600" />
                                                        </div>
                                                        <div>
                                                            <h4 className="text-white font-bold">{track.title}</h4>
                                                            <span className="text-[10px] text-zinc-600 uppercase font-black tracking-widest">Single Release</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-6">
                                                        <div className="flex items-center gap-2">
                                                            {track.isLocked ? (
                                                                <Lock size={16} className="text-zinc-600" />
                                                            ) : (
                                                                <Unlock size={16} className="text-violet-500/50" />
                                                            )}
                                                            <span className="text-white font-black">{track.price}</span>
                                                        </div>
                                                        <Button size="sm" variant={track.isLocked ? "outline" : "primary"} className="h-8 text-[9px] px-4">Buy now</Button>
                                                    </div>
                                                </div>
                                            )) : (
                                                <p className="py-12 text-center text-zinc-600 font-bold italic">No tracks released yet.</p>
                                            )}
                                        </div>
                                    )}

                                    {activeTab === "albums" && (
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                            {dj.albums.length > 0 ? dj.albums.map((album) => (
                                                <div key={album.id} className="p-6 rounded-3xl bg-zinc-900/30 border border-zinc-800 flex flex-col items-center text-center relative overflow-hidden group">
                                                    {album.isPremium && (
                                                        <div className="absolute top-4 right-4 px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30 text-[8px] font-black text-amber-500 uppercase tracking-widest">Premium</div>
                                                    )}
                                                    <div className="w-24 h-24 bg-violet-600/10 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                                        <Package size={40} className="text-violet-500" />
                                                    </div>
                                                    <h4 className="text-lg font-black text-white uppercase italic tracking-tighter mb-2">{album.title}</h4>
                                                    <span className="text-xs text-zinc-600 font-bold mb-6 italic">Full ZIP Pack + HQ Covers</span>
                                                    <Button variant="outline" size="sm" className="w-full">Get Access</Button>
                                                </div>
                                            )) : (
                                                <p className="col-span-full py-12 text-center text-zinc-600 font-bold italic">No albums available.</p>
                                            )}
                                        </div>
                                    )}

                                    {activeTab === "uploads" && (
                                        <div className="py-16 px-8 rounded-3xl bg-zinc-900/20 border-2 border-dashed border-zinc-800 flex flex-col items-center text-center">
                                            <div className="w-16 h-16 rounded-full bg-amber-500/10 flex items-center justify-center mb-6">
                                                <Crown size={32} className="text-amber-500" />
                                            </div>
                                            <h3 className="text-2xl font-black text-white uppercase italic tracking-tighter mb-4">LOCKED: FAN UPLOADS</h3>
                                            <p className="text-zinc-600 font-bold max-w-sm mb-8 italic">
                                                Exclusive remix attempts, stem files, and bootlegs uploaded by the community. Accessible to <span className="text-amber-500">Super</span> subscribers only.
                                            </p>
                                            <Button variant="primary" className="bg-amber-500 hover:bg-amber-600 shadow-[0_0_20px_rgba(245,158,11,0.2)]">Upgrade to Super</Button>
                                        </div>
                                    )}
                                </motion.div>
                            </AnimatePresence>
                        </div>

                        {/* Right Rail: Subscription Plans */}
                        <div className="space-y-8">
                            <div className="p-8 rounded-[2rem] bg-zinc-900 border border-zinc-800 shadow-2xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/5 blur-3xl rounded-full" />
                                <h3 className="text-xl font-black text-white uppercase italic tracking-tighter mb-2">Subscribe to {dj.name.split(' ')[0]}</h3>
                                <p className="text-zinc-500 text-sm font-bold mb-8">Unlock the storefront vault.</p>

                                <div className="space-y-4 mb-8">
                                    {plans.map((plan) => (
                                        <div key={plan.name} className={cn(
                                            "p-5 rounded-2xl border transition-all cursor-pointer group",
                                            plan.border || "border-zinc-800",
                                            plan.bg
                                        )}>
                                            <div className="flex justify-between items-start mb-4">
                                                <div className="flex items-center gap-3">
                                                    <plan.icon size={20} className={plan.color} />
                                                    <span className="text-sm font-black text-white uppercase tracking-widest">{plan.name}</span>
                                                </div>
                                                <div className="text-right">
                                                    <span className="text-lg font-black text-white tracking-tighter">{plan.price}</span>
                                                    <span className="block text-[8px] text-zinc-600 uppercase font-black">/ month</span>
                                                </div>
                                            </div>
                                            <p className="text-[10px] text-zinc-500 font-bold leading-relaxed mb-4 group-hover:text-zinc-300 transition-colors">
                                                {plan.quota}
                                            </p>
                                            <Button variant="outline" size="sm" className="w-full h-8 text-[9px]">Select Plan</Button>
                                        </div>
                                    ))}
                                </div>

                                <div className="flex items-center gap-3 p-4 rounded-xl bg-violet-500/5 border border-violet-500/10">
                                    <AlertCircle className="text-violet-400 shrink-0" size={16} />
                                    <p className="text-[10px] text-zinc-500 font-bold leading-tight">Subscriptions are purely UI mockups. No payments will be processed.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
