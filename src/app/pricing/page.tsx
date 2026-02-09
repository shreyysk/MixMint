"use client";

import React from "react";
import { Button } from "@/components/ui/Button";
import { Check, Zap, TrendingUp, Crown, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

const plans = [
    {
        name: "Basic",
        price: "₹99",
        tagline: "For the casual listener",
        icon: Zap,
        color: "text-zinc-400",
        iconBg: "from-zinc-600/20 to-zinc-600/5",
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
        iconBg: "from-violet-600/20 to-violet-600/5",
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
        price: "₹399",
        tagline: "For the ultimate supporter",
        icon: Crown,
        color: "text-amber-400",
        iconBg: "from-amber-600/20 to-amber-600/5",
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
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12">
                <div className="max-w-7xl mx-auto">
                    {/* Header */}
                    <div className="text-center mb-16 pt-4">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-medium mb-6"
                        >
                            Transparent Pricing
                        </motion.div>
                        <motion.h1
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
                            className="text-4xl md:text-5xl font-bold text-white mb-4"
                        >
                            Simple, <span className="text-violet-gradient">DJ-First</span> Pricing
                        </motion.h1>
                        <motion.p
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="text-zinc-500 max-w-2xl mx-auto"
                        >
                            MixMint is built on ownership. No streaming royalties here — just secure downloads and direct artist support.
                        </motion.p>
                    </div>

                    {/* Pricing Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
                        {plans.map((plan, i) => (
                            <motion.div
                                key={plan.name}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.1 + 0.2 }}
                                className={cn(
                                    "relative p-8 rounded-2xl bg-zinc-900/50 border flex flex-col transition-all duration-300 hover:bg-zinc-900/70",
                                    plan.border || "border-zinc-800/60",
                                    plan.popular && "ring-1 ring-violet-500/20"
                                )}
                            >
                                {plan.popular && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-violet-600 text-white text-xs font-medium shadow-lg shadow-violet-600/20">
                                        Most Popular
                                    </div>
                                )}

                                <div className="mb-8 text-center">
                                    <div className={cn(
                                        "inline-flex w-14 h-14 rounded-2xl bg-gradient-to-br items-center justify-center mb-5",
                                        plan.iconBg
                                    )}>
                                        <plan.icon className={plan.color} size={24} />
                                    </div>
                                    <h3 className="text-lg font-semibold text-white mb-1">{plan.name}</h3>
                                    <p className="text-zinc-500 text-sm mb-5">{plan.tagline}</p>
                                    <div className="flex items-baseline justify-center gap-1">
                                        <span className="text-4xl font-bold text-white">{plan.price}</span>
                                        <span className="text-zinc-500 text-sm">/ month</span>
                                    </div>
                                </div>

                                <div className="space-y-3 mb-8 flex-grow">
                                    {plan.features.map((feature) => (
                                        <div key={feature} className="flex items-start gap-3">
                                            <div className={cn(
                                                "mt-0.5 w-5 h-5 rounded-md flex items-center justify-center shrink-0",
                                                plan.popular ? "bg-violet-600/10 text-violet-400" : "bg-zinc-800 text-zinc-500"
                                            )}>
                                                <Check size={12} />
                                            </div>
                                            <span className="text-sm text-zinc-400 leading-tight">{feature}</span>
                                        </div>
                                    ))}
                                </div>

                                <Button
                                    variant={plan.popular ? "primary" : "outline"}
                                    className="w-full"
                                >
                                    Choose {plan.name}
                                </Button>
                            </motion.div>
                        ))}
                    </div>

                    {/* Info Section */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="max-w-4xl mx-auto p-8 md:p-10 rounded-2xl bg-zinc-900/40 border border-zinc-800/60"
                    >
                        <div className="flex flex-col md:flex-row items-start gap-8">
                            <div className="shrink-0 w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-600/20 to-violet-600/5 flex items-center justify-center">
                                <Info className="text-violet-400" size={24} />
                            </div>
                            <div>
                                <h4 className="text-xl font-semibold text-white mb-3">How it works</h4>
                                <p className="text-zinc-400 leading-relaxed mb-6">
                                    MixMint isn't like Spotify or Apple Music. When you subscribe or buy a track, you're getting{" "}
                                    <span className="text-white">permanent access</span> to high-fidelity audio files. Secure downloads ensure that even if you're offline at a gig or in the desert, your music is always yours.
                                </p>
                                <div className="flex flex-wrap gap-6 text-sm text-zinc-500">
                                    <span className="flex items-center gap-2">
                                        <Check size={16} className="text-violet-400" /> Secure Downloads
                                    </span>
                                    <span className="flex items-center gap-2">
                                        <Check size={16} className="text-violet-400" /> No Streaming Noise
                                    </span>
                                    <span className="flex items-center gap-2">
                                        <Check size={16} className="text-violet-400" /> Direct Support
                                    </span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
    );
}
