"use client";

import React from "react";
import Link from "next/link";
import {
  Download,
  Users,
  VolumeX,
  Zap,
  Compass,
  Music,
  CreditCard,
  ChevronRight,
  ArrowRight
} from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "@/app/components/ui/Button";
import { DJCard } from "@/app/components/ui/DJCard";
import { Footer } from "@/app/components/Footer";
import { motion } from "framer-motion";

const MOCK_DJS = [
  { name: "DJ Anish", genre: "Techno", image: "https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Sasha Vane", genre: "Deep House", image: "https://images.unsplash.com/photo-1594623121614-2909ac590859?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Arjun Pulse", genre: "Indo House", image: "https://images.unsplash.com/photo-1598387993281-cecf8368375d?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Mira Moon", genre: "Melodic Techno", image: "https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Rohan Rex", genre: "PsyTrance", image: "https://images.unsplash.com/photo-1514525253361-b83f8b9627c5?q=80&w=400&h=500&auto=format&fit=crop" },
  { name: "Neon Flux", genre: "Cyberpunk", image: "https://images.unsplash.com/photo-1459749411177-042180ce673c?q=80&w=400&h=500&auto=format&fit=crop" },
];

const FEATURES = [
  { icon: Download, title: "Secure Downloads", desc: "Permanent access to high-fidelity audio files after purchase.", color: "text-blue-400" },
  { icon: Users, title: "DJ Subscriptions", desc: "Follow your favorite artists for exclusive monthly drops.", color: "text-violet-400" },
  { icon: VolumeX, title: "No Streaming, No Noise", desc: "True ownership. Listen offline, anywhere, on any device.", color: "text-pink-400" },
  { icon: Zap, title: "Fair Earnings", desc: "DJs keep the majority of what they earn. Direct support.", color: "text-amber-400" },
];

const STEPS = [
  { icon: Compass, title: "Discover", desc: "Find unique artists" },
  { icon: Music, title: "Preview", desc: "Listen to demo clips" },
  { icon: ArrowRight, title: "Pay", desc: "Instant checkout" },
  { icon: Download, title: "Download", desc: "Ownership secured" },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-32">
      {/* 1. Hero Section */}
      <section className="relative pt-40 pb-20 px-6 md:px-12 overflow-hidden min-h-[90vh] flex items-center">
        {/* Abstract Background Glows */}
        <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] bg-violet-600/10 blur-[150px] rounded-full -z-10" />
        <div className="absolute bottom-[10%] left-[-5%] w-[400px] h-[400px] bg-purple-600/5 blur-[120px] rounded-full -z-10" />

        <div className="max-w-7xl mx-auto w-full">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-3xl"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-[10px] font-black uppercase tracking-[0.2em] mb-8">
              <Zap size={14} fill="currentColor" /> Direct Artist Support
            </div>
            <h1 className="text-6xl md:text-8xl font-black text-white leading-[0.9] tracking-tighter mb-8 uppercase italic">
              MixMint — <br />
              <span className="text-violet-gradient">Home of DJ</span> <br />
              Releases
            </h1>
            <p className="text-zinc-500 text-lg md:text-xl font-bold max-w-xl mb-12 leading-relaxed tracking-tight">
              Buy tracks, subscribe to DJs, and access exclusive drops — <span className="text-zinc-300">without the noise of streaming.</span>
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/explore">
                <Button size="lg" className="px-10 h-14">Explore DJs</Button>
              </Link>
              <Link href="/become-dj">
                <Button variant="outline" size="lg" className="px-10 h-14">Become a DJ</Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. Feature Highlights */}
      <section className="px-6 md:px-12 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
                className="p-8 rounded-3xl bg-zinc-900/40 border border-zinc-800 transition-all hover:bg-zinc-900/60 hover:border-zinc-700"
              >
                <Icon className={cn("mb-6", feature.color)} size={32} />
                <h3 className="text-white font-black uppercase italic tracking-tighter text-lg mb-3">{feature.title}</h3>
                <p className="text-zinc-500 text-sm font-bold leading-relaxed">{feature.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* 3. Featured DJs */}
      <section className="px-6 md:px-12 max-w-7xl mx-auto w-full">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16">
          <div>
            <h2 className="text-4xl md:text-5xl font-black text-white uppercase italic tracking-tighter mb-4">Featured Artists</h2>
            <p className="text-zinc-500 font-bold max-w-lg">Hand-picked legends and rising stars from India and beyond.</p>
          </div>
          <Link href="/explore">
            <Button variant="ghost" className="group gap-2">
              View All Artists <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {MOCK_DJS.map((dj, i) => (
            <DJCard key={dj.name} {...dj} />
          ))}
        </div>
      </section>

      {/* 4. How It Works */}
      <section className="px-6 md:px-12 py-24 bg-zinc-950/50 border-y border-zinc-900 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[1px] bg-gradient-to-r from-transparent via-violet-500 to-transparent opacity-20" />

        <div className="max-w-7xl mx-auto w-full text-center">
          <h2 className="text-4xl md:text-5xl font-black text-white uppercase italic tracking-tighter mb-20">The Ownership Flow</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-12 relative">
            {/* Connection lines (desktop only) */}
            <div className="hidden lg:block absolute top-12 left-[15%] right-[15%] h-[1px] border-t border-dashed border-zinc-800 -z-10" />

            {STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="flex flex-col items-center group">
                  <div className="w-24 h-24 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-8 shadow-xl transition-all group-hover:border-violet-600/50 group-hover:scale-110">
                    <Icon className="text-violet-500 group-hover:text-white transition-colors" size={32} />
                  </div>
                  <h4 className="text-white font-black uppercase tracking-tighter text-xl mb-2">{step.title}</h4>
                  <p className="text-zinc-600 text-sm font-bold">{step.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 md:px-12 mb-32">
        <div className="max-w-7xl mx-auto w-full rounded-[3rem] bg-gradient-to-br from-violet-600 to-indigo-700 p-12 md:p-24 text-center overflow-hidden relative">
          <div className="absolute inset-0 bg-black/10 backdrop-blur-3xl -z-10" />
          <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-white/10 blur-[100px] rounded-full" />

          <h2 className="text-5xl md:text-7xl font-black text-white uppercase italic tracking-tighter mb-8 max-w-4xl mx-auto leading-none">
            Ready to claim your sound?
          </h2>
          <p className="text-white/80 text-lg font-bold max-w-xl mx-auto mb-12">
            Join thousands of listeners supporting artists directly. No subscriptions required to start.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Button size="lg" className="bg-white text-violet-700 hover:bg-zinc-100 px-12 h-16">Get Started</Button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
