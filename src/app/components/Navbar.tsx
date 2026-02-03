"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Headphones } from "lucide-react";
import { cn } from "@/app/lib/utils";
import { Button } from "./ui/Button";
import { useAuth } from "@/app/lib/AuthContext";
import { signOut } from "@/app/lib/auth";

const navLinks = [
    { name: "Explore", href: "/explore" },
    { name: "Tracks", href: "/tracks" },
    { name: "Albums", href: "/albums" },
    { name: "Pricing", href: "/pricing" },
];

export function Navbar() {
    const [isOpen, setIsOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const pathname = usePathname();
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
                "fixed top-0 left-0 right-0 z-50 transition-all duration-300 px-4 md:px-8",
                scrolled ? "py-2" : "py-4"
            )}
        >
            <div className={cn(
                "max-w-7xl mx-auto h-14 flex items-center justify-between px-6 rounded-2xl transition-all duration-300",
                scrolled ? "glass" : "bg-transparent"
            )}>
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2.5 group">
                    <div className="w-9 h-9 bg-gradient-to-br from-violet-500 to-violet-700 rounded-xl flex items-center justify-center group-hover:rotate-6 transition-transform shadow-lg shadow-violet-600/20">
                        <Headphones className="text-white" size={18} />
                    </div>
                    <span className="text-lg font-bold tracking-tight text-white">MixMint</span>
                </Link>

                {/* Desktop Nav */}
                <div className="hidden md:flex items-center gap-1">
                    {navLinks.map((link) => (
                        <Link
                            key={link.href}
                            href={link.href}
                            className={cn(
                                "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                                pathname === link.href 
                                    ? "text-white bg-zinc-800/60" 
                                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/40"
                            )}
                        >
                            {link.name}
                        </Link>
                    ))}
                </div>

                {/* Desktop Auth */}
                <div className="hidden md:flex items-center gap-3">
                    {!loading && !user && (
                        <>
                            <Link href="/auth/login">
                                <Button variant="ghost" size="sm">Log In</Button>
                            </Link>
                            <Link href="/auth/signup">
                                <Button size="sm">Sign Up</Button>
                            </Link>
                        </>
                    )}

                    {!loading && user && (
                        <div className="flex items-center gap-3">
                            <span className="text-sm text-zinc-400 font-medium hidden lg:block">
                                {user.email}
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={async () => {
                                    await signOut();
                                    window.location.href = "/";
                                }}
                                className="text-zinc-400 hover:text-red-400"
                            >
                                Logout
                            </Button>
                        </div>
                    )}
                </div>

                {/* Mobile Toggle */}
                <button
                    className="md:hidden w-10 h-10 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-800/60 transition-colors"
                    onClick={() => setIsOpen(!isOpen)}
                >
                    {isOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
            </div>

            {/* Mobile Menu */}
            {isOpen && (
                <div className="absolute top-20 left-4 right-4 glass p-6 rounded-2xl md:hidden animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="flex flex-col gap-2">
                        {navLinks.map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                onClick={() => setIsOpen(false)}
                                className={cn(
                                    "px-4 py-3 rounded-xl text-sm font-medium transition-colors",
                                    pathname === link.href 
                                        ? "text-white bg-zinc-800/60" 
                                        : "text-zinc-400 hover:text-white hover:bg-zinc-800/40"
                                )}
                            >
                                {link.name}
                            </Link>
                        ))}
                        <hr className="border-zinc-800 my-3" />
                        <div className="flex flex-col gap-2">
                            {!loading && !user && (
                                <>
                                    <Link href="/auth/login" onClick={() => setIsOpen(false)}>
                                        <Button variant="outline" className="w-full">Log In</Button>
                                    </Link>
                                    <Link href="/auth/signup" onClick={() => setIsOpen(false)}>
                                        <Button className="w-full">Sign Up</Button>
                                    </Link>
                                </>
                            )}
                            {!loading && user && (
                                <Button
                                    variant="outline"
                                    onClick={async () => {
                                        await signOut();
                                        setIsOpen(false);
                                        window.location.href = "/";
                                    }}
                                    className="w-full"
                                >
                                    Logout
                                </Button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}