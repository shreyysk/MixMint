"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Headphones, Mail, Lock, Music } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { motion } from "framer-motion";
import { signIn } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export default function LoginPage() {
    const router = useRouter();
    const { signInWithGoogle } = useAuth();
    // 1. Add state for email and password
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    // 2. The requested handler logic
    const handleLogin = async () => {
        try {
            await signIn(email, password);
            router.push("/dashboard");
        } catch (err: any) {
            alert(err.message);
        }
    };

    return (
        <div className="min-h-screen bg-[#0B0B0F] flex flex-col justify-center py-12 px-6 lg:px-8 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-violet-600/5 blur-[120px] rounded-full -z-10" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-600/5 blur-[120px] rounded-full -z-10" />

            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <Link href="/" className="flex items-center justify-center gap-2 group mb-8">
                    <div className="w-12 h-12 bg-violet-600 rounded-xl flex items-center justify-center group-hover:rotate-6 transition-transform shadow-[0_0_20px_rgba(124,58,237,0.4)]">
                        <Headphones className="text-white" size={28} />
                    </div>
                    <span className="text-2xl font-black tracking-tighter text-white uppercase italic">MixMint</span>
                </Link>
                <h2 className="text-center text-4xl font-black text-white uppercase italic tracking-tighter mb-2">Welcome Back</h2>
                <p className="text-center text-zinc-500 font-bold mb-10 italic">Secure access to your DJ vault.</p>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="sm:mx-auto sm:w-full sm:max-w-md"
            >
                <div className="bg-zinc-900/40 border border-zinc-800 py-10 px-8 shadow-2xl rounded-[2.5rem] backdrop-blur-xl">
                    <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
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
                                    // Connected state
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="name@example.com"
                                    className="block w-full bg-zinc-950 border border-zinc-800 rounded-2xl pl-12 pr-4 py-4 text-white placeholder-zinc-700 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-medium"
                                />
                            </div>
                        </div>

                        <div>
                            <div className="flex items-center justify-between mb-3 ml-1">
                                <label htmlFor="password" className="block text-xs font-black text-zinc-500 uppercase tracking-widest">
                                    Password
                                </label>
                                <div className="text-xs">
                                    <Link href="#" className="font-black text-violet-500 hover:text-violet-400 uppercase tracking-tight">
                                        Forgot password?
                                    </Link>
                                </div>
                            </div>
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-zinc-600 group-focus-within:text-violet-500 transition-colors" />
                                </div>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    // Connected state
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="block w-full bg-zinc-950 border border-zinc-800 rounded-2xl pl-12 pr-4 py-4 text-white placeholder-zinc-700 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-medium"
                                />
                            </div>
                        </div>

                        <div>
                            {/* Connected logic to onClick */}
                            <Button
                                type="button"
                                onClick={handleLogin}
                                className="w-full h-14 rounded-2xl text-base shadow-[0_0_20px_rgba(124,58,237,0.2)]"
                            >
                                Login to Account
                            </Button>
                        </div>

                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-zinc-800" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-[#0B0B0F] px-2 text-zinc-500 font-black tracking-widest leading-none">Or continue with</span>
                            </div>
                        </div>

                        <Button
                            type="button"
                            variant="secondary"
                            onClick={signInWithGoogle}
                            className="w-full h-14 rounded-2xl text-base border-zinc-800 bg-zinc-950 hover:bg-zinc-900 flex items-center justify-center gap-3 group"
                        >
                            <svg className="w-5 h-5 group-hover:scale-110 transition-transform" viewBox="0 0 24 24">
                                <path
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                    fill="#4285F4"
                                />
                                <path
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                    fill="#34A853"
                                />
                                <path
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                    fill="#FBBC05"
                                />
                                <path
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z"
                                    fill="#EA4335"
                                />
                            </svg>
                            <span className="font-bold">Google</span>
                        </Button>
                    </form>

                    <div className="mt-10 pt-10 border-t border-zinc-800/50">
                        <p className="text-center text-sm text-zinc-500 font-bold">
                            New to MixMint?{' '}
                            <Link href="/auth/signup" className="text-violet-500 hover:text-violet-400 uppercase font-black tracking-tight ml-1">
                                Create Account
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Secondary Info */}
                <div className="mt-8 flex items-center justify-center gap-6 text-[10px] text-zinc-600 font-black uppercase tracking-[0.2em]">
                    <span className="flex items-center gap-1.5"><Music size={12} /> Pure Audio</span>
                    <span className="h-1 w-1 rounded-full bg-zinc-800" />
                    <span>Secure Vault</span>
                </div>
            </motion.div>
        </div>
    );
}