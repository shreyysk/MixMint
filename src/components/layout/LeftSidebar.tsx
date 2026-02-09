"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";
import {
    Home,
    Flame,
    Library,
    Package,
    Star,
    Plus,
    ChevronRight,
    Headphones
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

interface SubscribedDJ {
    id: string;
    dj_name: string;
    slug: string;
}

const NAV_ITEMS = [
    { href: "/", label: "Discover", icon: Home },
    { href: "/explore", label: "Trending DJs", icon: Flame },
    { href: "/my-collection", label: "Your Collection", icon: Library },
    { href: "/my-collection?tab=purchases", label: "My Purchases", icon: Package },
    { href: "/my-collection?tab=subscriptions", label: "Subscriptions", icon: Star },
];

export function LeftSidebar() {
    const pathname = usePathname();
    const { user } = useAuth();
    const [subscribedDJs, setSubscribedDJs] = useState<SubscribedDJ[]>([]);
    const [isCollapsed, setIsCollapsed] = useState(false);

    useEffect(() => {
        if (user) {
            fetchSubscribedDJs();
        }
    }, [user]);

    async function fetchSubscribedDJs() {
        const { data } = await supabase
            .from('dj_subscriptions')
            .select(`
        dj_id,
        dj_profiles:dj_id (
          id,
          dj_name,
          slug
        )
      `)
            .eq('user_id', user?.id)
            .gte('expires_at', new Date().toISOString())
            .limit(5);

        if (data) {
            const djs = data
                .map((sub: any) => sub.dj_profiles)
                .filter(Boolean) as SubscribedDJ[];
            setSubscribedDJs(djs);
        }
    }

    return (
        <motion.aside
            initial={{ x: -240 }}
            animate={{ x: 0 }}
            className={cn(
                "fixed left-0 top-0 h-screen bg-surface-dark/80 backdrop-blur-xl border-r border-white/5",
                "flex flex-col z-40 transition-all duration-300",
                isCollapsed ? "w-16" : "w-60"
            )}
        >
            {/* Logo */}
            <div className="p-6 border-b border-white/5">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-purple-mint flex items-center justify-center">
                        <Headphones size={20} className="text-white" />
                    </div>
                    {!isCollapsed && (
                        <span className="text-xl font-heading font-bold text-white">
                            Mix<span className="text-purple-primary">Mint</span>
                        </span>
                    )}
                </Link>
            </div>

            {/* Main Navigation */}
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href.split("?")[0]));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                                isActive
                                    ? "bg-purple-primary/20 text-purple-primary-dark shadow-purple-glow"
                                    : "text-zinc-400 hover:text-white hover:bg-white/5"
                            )}
                        >
                            <Icon size={20} />
                            {!isCollapsed && (
                                <span className="font-medium text-sm">{item.label}</span>
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Subscribed DJs Section */}
            {!isCollapsed && user && (
                <div className="p-4 border-t border-white/5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-3 px-4">
                        Your DJs
                    </h3>
                    <div className="space-y-1">
                        {subscribedDJs.length > 0 ? (
                            subscribedDJs.map((dj) => (
                                <Link
                                    key={dj.id}
                                    href={`/dj/${dj.slug}`}
                                    className="flex items-center gap-3 px-4 py-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                                >
                                    <ChevronRight size={14} className="text-mint-accent" />
                                    <span className="text-sm truncate">{dj.dj_name}</span>
                                </Link>
                            ))
                        ) : (
                            <p className="text-xs text-zinc-600 px-4">No subscriptions yet</p>
                        )}
                        <Link
                            href="/explore"
                            className="flex items-center gap-3 px-4 py-2 rounded-lg text-mint-accent hover:text-mint-accent-dark hover:bg-mint-accent/5 transition-colors"
                        >
                            <Plus size={14} />
                            <span className="text-sm font-medium">Browse More</span>
                        </Link>
                    </div>
                </div>
            )}
        </motion.aside>
    );
}
