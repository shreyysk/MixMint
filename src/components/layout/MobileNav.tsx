"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, Search, Package, Star, User } from "lucide-react";

const MOBILE_NAV_ITEMS = [
    { href: "/", label: "Home", icon: Home },
    { href: "/explore", label: "Search", icon: Search },
    { href: "/my-collection?tab=purchases", label: "Purchases", icon: Package },
    { href: "/my-collection?tab=subscriptions", label: "Subs", icon: Star },
    { href: "/account", label: "Account", icon: User },
];

export function MobileNav() {
    const pathname = usePathname();

    return (
        <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden">
            <div className="bg-surface-dark/95 backdrop-blur-xl border-t border-white/5 px-2 pb-safe">
                <div className="flex items-center justify-around py-2">
                    {MOBILE_NAV_ITEMS.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href ||
                            (item.href !== "/" && pathname.startsWith(item.href.split("?")[0]));

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all",
                                    isActive
                                        ? "text-purple-primary"
                                        : "text-zinc-500"
                                )}
                            >
                                <Icon size={22} />
                                <span className="text-[10px] font-medium">{item.label}</span>
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
