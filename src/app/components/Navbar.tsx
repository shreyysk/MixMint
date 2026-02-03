"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Headphones } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "./ui/Button";
// 1. Ensure imports are present
import { useAuth } from "@/app/lib/AuthContext";
import { signOut } from "@/app/lib/auth";

const navLinks = [
    { name: "Explore DJs", href: "/explore" },
    { name: "Tracks", href: "/tracks" },
    { name: "Albums", href: "/albums" },
    { name: "Pricing", href: "/pricing" },
];

export function Navbar() {
    const [isOpen, setIsOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const pathname = usePathname();
    
    // 2. Add auth hook
    const { user, loading } = useAuth();

    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <nav
            className={cn(
                "fixed top-0 left-0 right-0 z-50 transition-all duration-300 px-6 md:px-12",
                scrolled ? "h-16 glass mt-4 mx-4 rounded-2xl md:mx-12" : "h-24 bg-transparent"
            )}
        >
            <div className="max-w-7xl mx-auto h-full flex items-center justify-between">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2 group">
                    <div className="w-10 h-10 bg-violet-600 rounded-lg flex items-center justify-center group-hover:rotate-6 transition-transform shadow-[0_0_15px_rgba(124,58,237,0.5)]">
                        <Headphones className="text-white" size={24} />
                    </div>
                    <span className="text-xl font-black tracking-tighter text-white uppercase italic">MixMint</span>
                </Link>

                {/* Desktop Nav */}
                <div className="hidden md:flex items-center gap-8">
                    {navLinks.map((link) => (
                        <Link
                            key={link.href}
                            href={link.href}
                            className={cn(
                                "text-xs font-black uppercase tracking-widest transition-colors hover:text-violet-400",
                                pathname === link.href ? "text-violet-500" : "text-zinc-500"
                            )}
                        >
                            {link.name}
                        </Link>
                    ))}
                </div>

                {/* Desktop Auth - 3. Replaced logic with requested pattern */}
                <div className="hidden md:flex items-center gap-4 text-white font-bold text-sm">
                    {!loading && !user && (
                        <>
                            <a href="/auth/login" className="hover:text-violet-400">Login</a>
                            <a href="/auth/signup" className="bg-white text-black px-4 py-2 rounded-full hover:bg-gray-200 transition-colors">Sign Up</a>
                        </>
                    )}

                    {!loading && user && (
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-green-400">
                        {user.email}
                        </span>

                        <button
                        className="text-sm text-red-400 hover:text-red-300"
                        onClick={async () => {
                            await signOut();
                            window.location.href = "/";
                        }}
                        >
                        Logout
                        </button>
                    </div>
                    )}

                </div>

                {/* Mobile Toggle */}
                <button
                    className="md:hidden text-zinc-400 hover:text-white"
                    onClick={() => setIsOpen(!isOpen)}
                >
                    {isOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {/* Mobile Menu */}
            {isOpen && (
                <div className="absolute top-20 left-4 right-4 glass p-6 rounded-2xl md:hidden animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="flex flex-col gap-6">
                        {navLinks.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                onClick={() => setIsOpen(false)}
                                className={cn(
                                    "text-xs font-black uppercase tracking-widest",
                                    pathname === link.href ? "text-violet-500" : "text-zinc-400"
                                )}
                            >
                                {link.name}
                            </Link>
                        ))}
                        <hr className="border-zinc-800" />
                        <div className="flex flex-col gap-3">
                            <Link href="/auth/login" onClick={() => setIsOpen(false)}>
                                <Button variant="outline" className="w-full">Login</Button>
                            </Link>
                            <Link href="/auth/signup" onClick={() => setIsOpen(false)}>
                                <Button className="w-full">Sign Up</Button>
                            </Link>
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}