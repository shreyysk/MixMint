"use client";

import React from "react";
import { Button } from "@/app/components/ui/Button";
import { Check, Zap, TrendingUp, Crown, Info } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { motion } from "framer-motion";

const plans = [
    {
        name: "Basic",
        price: "₹99",
        tagline: "For the causal listener",
        icon: Zap,
        color: "text-zinc-400",
        bg: "bg-zinc-900/50",
        features: [
            "3 High-Quality Downloads / mo",
            "Standard Community Access",
            "Basic Artist Profile Access",
            "Mobile & Desktop Ready"
        ]
    },
    {
        name: "Pro",
        price: "₹199",
        tagline: "For the dedicated fan",
        icon: TrendingUp,
        color: "text-violet-400",
        bg: "bg-violet-900/10",
        border: "border-violet-500/30",
        popular: true,
        features: [
            "10 High-Quality Downloads / mo",
            "Early Access to Releases",
            "Exclusive Track Previews",
            "Priority Community Support",
            "No Ads, Direct Artist Support"
        ]
    },
    {
        name: "Super",
        price: "399",
        tagline: "For the ultimate supporter",
        icon: Crown,
        color: "text-amber-400",
        bg: "bg-amber-900/10",
        border: "border-amber-500/30",
        features: [
            "Unlimited HQ Downloads",
            "Fan Uploads Access (Stem Files)",
            "Direct Message to DJ",
            "VIP Event Invitations",
            "Limited Edition Digital Merch"
        ]
    }
];

export default function PricingPage() {
    return (
        <div className="pb-24">
            <div className="px-6 md:px-12">
                <div className="max-w-7xl mx-auto">
                    {/* Header */}
                    <div className="text-center mb-20">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-[10px] font-black uppercase tracking-[0.2em] mb-8"
                        >
                            Transparent Pricing
                        </motion.div>
                        <h1 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-6">
                            Simple, <span className="text-violet-gradient">DJ-First</span> Pricing
                        </h1>
                        <p className="text-zinc-500 font-bold max-w-2xl mx-auto text-lg leading-relaxed">
                            MixMint is built on ownership. No streaming royalties here — <span className="text-zinc-300">just secure downloads and direct artist support.</span>
                        </p>
                    </div>

                    {/* Pricing Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-24">
                        {plans.map((plan, i) => (
                            <motion.div
                                key={plan.name}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.1 }}
                                className={cn(
                                    "relative p-8 rounded-[2.5rem] border flex flex-col transition-all hover:scale-[1.02] duration-300",
                                    plan.border || "border-zinc-800",
                                    plan.bg
                                )}
                            >
                                {plan.popular && (
                                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-violet-600 text-white text-[10px] font-black uppercase tracking-widest shadow-[0_0_15px_rgba(124,58,237,0.5)]">
                                        Most Popular
                                    </div>
                                )}

                                <div className="mb-10 text-center">
                                    <div className={cn("inline-flex p-4 rounded-2xl bg-black/40 border border-zinc-800 mb-6", plan.color)}>
                                        <plan.icon size={32} />
                                    </div>
                                    <h3 className="text-xl font-black text-white uppercase tracking-widest mb-2">{plan.name}</h3>
                                    <p className="text-zinc-500 text-sm font-bold italic mb-6">{plan.tagline}</p>
                                    <div className="flex items-baseline justify-center gap-1">
                                        <span className="text-4xl font-black text-white italic tracking-tighter">{plan.price}</span>
                                        <span className="text-zinc-600 text-sm font-black uppercase">/ month</span>
                                    </div>
                                </div>

                                <div className="space-y-4 mb-10 flex-grow">
                                    {plan.features.map((feature) => (
                                        <div key={feature} className="flex items-start gap-3">
                                            <div className={cn("mt-1 p-0.5 rounded-full bg-zinc-900 border border-zinc-800", plan.popular ? "text-violet-400" : "text-zinc-600")}>
                                                <Check size={12} />
                                            </div>
                                            <span className="text-sm text-zinc-400 font-bold leading-tight">{feature}</span>
                                        </div>
                                    ))}
                                </div>

                                <Button
                                    variant={plan.popular ? "primary" : "outline"}
                                    className={cn("w-full h-14 rounded-2xl", plan.popular ? "bg-violet-600 hover:bg-violet-700" : "border-zinc-800")}
                                >
                                    Choose {plan.name}
                                </Button>
                            </motion.div>
                        ))}
                    </div>

                    {/* Info Section */}
                    <div className="max-w-4xl mx-auto p-8 md:p-12 rounded-[3rem] bg-zinc-900/30 border border-zinc-800 text-center md:text-left">
                        <div className="flex flex-col md:flex-row items-center gap-10">
                            <div className="shrink-0 w-20 h-20 rounded-full bg-violet-600/10 border border-violet-500/20 flex items-center justify-center">
                                <Info className="text-violet-500" size={32} />
                            </div>
                            <div>
                                <h4 className="text-2xl font-black text-white uppercase italic tracking-tighter mb-4">How it works</h4>
                                <p className="text-zinc-500 font-bold leading-relaxed mb-6">
                                    MixMint isn't like Spotify or Apple Music. When you subscribe or buy a track, you're getting <span className="text-white italic">permanent access</span> to high-fidelity audio files. Secure downloads ensure that even if you're offline at a gig or in the desert, your music is always yours.
                                </p>
                                <div className="flex flex-wrap gap-8 text-[10px] text-zinc-400 font-black uppercase tracking-[0.2em]">
                                    <span className="flex items-center gap-2"><Check size={14} className="text-violet-500" /> Secure Downloads</span>
                                    <span className="flex items-center gap-2"><Check size={14} className="text-violet-500" /> No Streaming Noise</span>
                                    <span className="flex items-center gap-2"><Check size={14} className="text-violet-500" /> Direct Support</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
