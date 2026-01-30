"use client";

import React from "react";
import Link from "next/link";
import { Headphones, Mail, Lock, User, ShieldCheck } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import { motion } from "framer-motion";

export default function SignupPage() {
    return (
        <div className="min-h-screen bg-[#0B0B0F] flex flex-col justify-center py-12 px-6 lg:px-8 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-violet-600/5 blur-[120px] rounded-full -z-10" />
            <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-indigo-600/5 blur-[120px] rounded-full -z-10" />

            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <Link href="/" className="flex items-center justify-center gap-2 group mb-8">
                    <div className="w-12 h-12 bg-violet-600 rounded-xl flex items-center justify-center group-hover:rotate-6 transition-transform shadow-[0_0_20px_rgba(124,58,237,0.4)]">
                        <Headphones className="text-white" size={28} />
                    </div>
                    <span className="text-2xl font-black tracking-tighter text-white uppercase italic">MixMint</span>
                </Link>
                <h2 className="text-center text-4xl font-black text-white uppercase italic tracking-tighter mb-2">Join the Community</h2>
                <p className="text-center text-zinc-500 font-bold mb-10 italic">Start supporting your favorite DJs directly.</p>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="sm:mx-auto sm:w-full sm:max-w-md"
            >
                <div className="bg-zinc-900/40 border border-zinc-800 py-10 px-8 shadow-2xl rounded-[2.5rem] backdrop-blur-xl">
                    <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
                        <div>
                            <label htmlFor="name" className="block text-xs font-black text-zinc-500 uppercase tracking-widest mb-3 ml-1">
                                Full Name
                            </label>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <User className="h-5 w-5 text-zinc-600 group-focus-within:text-violet-500 transition-colors" />
                                </div>
                                <input
                                    id="name"
                                    name="name"
                                    type="text"
                                    placeholder="Arjun Singh"
                                    className="block w-full bg-zinc-950 border border-zinc-800 rounded-2xl pl-12 pr-4 py-4 text-white placeholder-zinc-700 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-medium"
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-xs font-black text-zinc-500 uppercase tracking-widest mb-3 ml-1">
                                Email Address
                            </label>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Mail className="h-5 w-5 text-zinc-600 group-focus-within:text-violet-500 transition-colors" />
                                </div>
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    className="block w-full bg-zinc-950 border border-zinc-800 rounded-2xl pl-12 pr-4 py-4 text-white placeholder-zinc-700 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-medium"
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-xs font-black text-zinc-500 uppercase tracking-widest mb-3 ml-1">
                                Password
                            </label>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-zinc-600 group-focus-within:text-violet-500 transition-colors" />
                                </div>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    placeholder="Create a strong password"
                                    className="block w-full bg-zinc-950 border border-zinc-800 rounded-2xl pl-12 pr-4 py-4 text-white placeholder-zinc-700 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-medium"
                                />
                            </div>
                        </div>

                        <div className="pt-2">
                            <Button type="button" className="w-full h-14 rounded-2xl text-base shadow-[0_0_20px_rgba(124,58,237,0.2)]">
                                Create Account
                            </Button>
                        </div>

                        <p className="text-[10px] text-zinc-600 font-bold leading-relaxed text-center px-4">
                            By joining, you agree to our <Link href="#" className="underline hover:text-zinc-400">Terms of Service</Link> and <Link href="#" className="underline hover:text-zinc-400">Privacy Policy</Link>.
                        </p>
                    </form>

                    <div className="mt-10 pt-10 border-t border-zinc-800/50">
                        <p className="text-center text-sm text-zinc-500 font-bold">
                            Already have an account?{' '}
                            <Link href="/auth/login" className="text-violet-500 hover:text-violet-400 uppercase font-black tracking-tight ml-1">
                                Login here
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Trust badge */}
                <div className="mt-8 flex items-center justify-center gap-2 text-[10px] text-zinc-600 font-black uppercase tracking-[0.2em]">
                    <ShieldCheck size={14} className="text-violet-500/50" />
                    <span>Secure P2P Community</span>
                </div>
            </motion.div>
        </div>
    );
}
