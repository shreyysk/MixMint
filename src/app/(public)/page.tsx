"use client";

import React from "react";
import Link from "next/link";
import {
  Download,
  Users,
  Shield,
  Zap,
  Compass,
  Music,
  ArrowRight,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "@/app/components/ui/Button";
import { DJCard } from "@/app/components/ui/DJCard";
import { motion } from "framer-motion";

const MOCK_DJS = [
  { name: "DJ Anish", slug: "dj-anish", genre: ["Techno", "House"], image: "https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Sasha Vane", slug: "sasha-vane", genre: ["Deep House", "EDM"], image: "https://images.unsplash.com/photo-1594623121614-2909ac590859?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Arjun Pulse", slug: "arjun-pulse", genre: ["Indo House"], image: "https://images.unsplash.com/photo-1598387993281-cecf8368375d?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Mira Moon", slug: "mira-moon", genre: ["Melodic Techno"], image: "https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Rohan Rex", slug: "rohan-rex", genre: ["PsyTrance", "Techno"], image: "https://images.unsplash.com/photo-1514525253361-b83f8b9627c5?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Neon Flux", slug: "neon-flux", genre: ["Cyberpunk"], image: "https://images.unsplash.com/photo-1459749411177-042180ce673c?q=80&w=400&h=500&auto=format&fit=crop" },
];

const FEATURES = [
  { icon: Download, title: "Secure Downloads", desc: "Permanent access to high-fidelity audio files after purchase.", color: "text-violet-400", bg: "from-violet-600/20 to-violet-600/5" },
  { icon: Users, title: "DJ Subscriptions", desc: "Follow your favorite artists for exclusive monthly drops.", color: "text-blue-400", bg: "from-blue-600/20 to-blue-600/5" },
  { icon: Shield, title: "True Ownership", desc: "No streaming noise. Listen offline, on any device, forever.", color: "text-emerald-400", bg: "from-emerald-600/20 to-emerald-600/5" },
  { icon: Zap, title: "Direct Support", desc: "DJs keep the majority of earnings. Support artists directly.", color: "text-amber-400", bg: "from-amber-600/20 to-amber-600/5" },
];

const STEPS = [
  { icon: Compass, title: "Discover", desc: "Find unique artists" },
  { icon: Music, title: "Preview", desc: "Listen to demos" },
  { icon: ArrowRight, title: "Purchase", desc: "Instant checkout" },
  { icon: Download, title: "Download", desc: "Ownership secured" },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col pb-24">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center px-6 md:px-12 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute top-[15%] right-[-15%] w-[600px] h-[600px] bg-violet-600/8 blur-[180px] rounded-full pointer-events-none" />
        <div className="absolute bottom-[10%] left-[-10%] w-[500px] h-[500px] bg-blue-600/5 blur-[150px] rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto w-full">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="max-w-3xl"
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-medium mb-8">
              <Sparkles size={14} />
              <span>Direct Artist Support Platform</span>
            </div>

            {/* Headline */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white leading-[1.1] tracking-tight mb-6">
              MixMint —{" "}
              <span className="text-violet-gradient">Home of DJ</span>{" "}
              Releases
            </h1>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-zinc-400 max-w-xl mb-10 leading-relaxed">
              Buy tracks, subscribe to DJs, and access exclusive drops —{" "}
              <span className="text-zinc-200">without the noise of streaming.</span>
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap gap-4">
              <Link href="/explore">
                <Button size="lg" className="px-8">
                  Explore DJs
                  <ChevronRight size={18} />
                </Button>
              </Link>
              <Link href="/dj/apply">
                <Button variant="outline" size="lg" className="px-8">
                  Become a DJ
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="px-6 md:px-12 py-24">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map((feature, i) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/60 hover:border-zinc-700/60 transition-all duration-300"
                >
                  <div className={cn("w-11 h-11 rounded-xl bg-gradient-to-br flex items-center justify-center mb-5", feature.bg)}>
                    <Icon className={feature.color} size={20} />
                  </div>
                  <h3 className="text-white font-semibold text-base mb-2">{feature.title}</h3>
                  <p className="text-zinc-500 text-sm leading-relaxed">{feature.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Featured DJs Section */}
      <section className="px-6 md:px-12 py-16">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-3">Featured Artists</h2>
              <p className="text-zinc-500 max-w-lg">Hand-picked legends and rising stars from the scene.</p>
            </div>
            <Link href="/explore">
              <Button variant="ghost" className="group">
                View All
                <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </div>

          {/* DJ Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {MOCK_DJS.map((dj) => (
              <DJCard key={dj.slug} {...dj} />
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="px-6 md:px-12 py-24 bg-zinc-950/50 border-y border-zinc-800/40">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-16">How It Works</h2>
          </motion.div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 relative">
            {/* Connection Line */}
            <div className="hidden lg:block absolute top-12 left-[15%] right-[15%] h-px border-t border-dashed border-zinc-700/60" />

            {STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                  className="flex flex-col items-center group"
                >
                  <div className="w-20 h-20 rounded-2xl bg-zinc-900/80 border border-zinc-800 flex items-center justify-center mb-5 group-hover:border-violet-500/50 group-hover:scale-105 transition-all duration-300">
                    <Icon className="text-violet-400 group-hover:text-violet-300" size={28} />
                  </div>
                  <h4 className="text-white font-semibold mb-1">{step.title}</h4>
                  <p className="text-zinc-600 text-sm">{step.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 md:px-12 py-24">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative p-10 md:p-16 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-700 text-center overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-white/10 blur-[100px] rounded-full pointer-events-none" />
            
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 max-w-2xl mx-auto leading-tight">
              Ready to claim your sound?
            </h2>
            <p className="text-white/80 text-lg max-w-xl mx-auto mb-10">
              Join listeners supporting artists directly. No subscription required to start.
            </p>
            <Link href="/auth/signup">
              <Button size="lg" className="bg-white text-violet-700 hover:bg-zinc-100 px-10">
                Get Started
                <ArrowRight size={18} />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
