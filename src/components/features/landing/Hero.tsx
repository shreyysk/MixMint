'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Play, Sparkles, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export const Hero = () => {
    return (
        <section className="relative pt-20 pb-16 overflow-hidden">
            {/* Ambient Backgrounds */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-purple-primary/10 blur-[120px] rounded-full -z-10 animate-pulse" />
            <div className="absolute top-[20%] right-0 w-[400px] h-[400px] bg-mint-accent/5 blur-[100px] rounded-full -z-10" />

            <div className="container mx-auto px-6 text-center space-y-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-md"
                >
                    <Sparkles size={14} className="text-purple-primary" />
                    <span className="text-[10px] font-black text-zinc-300 uppercase tracking-[0.3em]">Direct-to-Fan DJ Marketplace</span>
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.1 }}
                    className="text-6xl md:text-8xl font-black text-white italic uppercase tracking-tighter leading-[0.9]"
                >
                    Redefining <br />
                    <span className="text-gradient-purple">Digital</span> <span className="text-gradient-mint">Audio</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="max-w-2xl mx-auto text-zinc-400 text-lg md:text-xl font-bold leading-relaxed"
                >
                    Join the next generation of DJs. Sell directly to your tribe,
                    keep more of your revenue, and build a community that lasts.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.3 }}
                    className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
                >
                    <Link href="/explore">
                        <Button size="lg" className="h-16 px-10 rounded-2xl bg-white text-black hover:bg-zinc-200 text-lg font-black uppercase tracking-widest shadow-white-glow">
                            Explore Drops
                        </Button>
                    </Link>
                    <Link href="/auth/signup">
                        <Button size="lg" variant="ghost" className="h-16 px-10 rounded-2xl border border-white/10 text-white hover:bg-white/5 text-lg font-black uppercase tracking-widest">
                            Join as Artist
                        </Button>
                    </Link>
                </motion.div>

                {/* Floating Stats */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 1.5, delay: 0.5 }}
                    className="flex items-center justify-center gap-12 pt-12"
                >
                    <div className="text-center">
                        <p className="text-2xl font-black text-white">₹0</p>
                        <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Fees for Fans</p>
                    </div>
                    <div className="w-px h-12 bg-white/10" />
                    <div className="text-center">
                        <p className="text-2xl font-black text-white italic">85%</p>
                        <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Artists Split</p>
                    </div>
                    <div className="w-px h-12 bg-white/10" />
                    <div className="text-center">
                        <p className="text-2xl font-black text-white">24/96</p>
                        <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Hi-Res Audio</p>
                    </div>
                </motion.div>
            </div>
        </section>
    );
};
