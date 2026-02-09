
"use client";

import Link from "next/link";
import { useAuth } from "@/app/lib/AuthContext";
import { Button } from "@/app/components/ui/Button";
import { LogOut, User, Music, Mic, BarChart, Settings, Library } from "lucide-react";
import { motion } from "framer-motion";
import { usePathname } from 'next/navigation';
import { cn } from "@/app/lib/utils";

const NAV_LINKS = [
  { href: "/tracks", label: "Tracks", icon: Music },
  { href: "/explore", label: "Explore DJs", icon: Mic },
];

export function Navbar() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();

  return (
    <motion.header 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="sticky top-4 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 bg-zinc-900/50 backdrop-blur-xl border border-zinc-800/50 rounded-2xl px-6">
          <div className="flex items-center gap-10">
            <Link href="/" className="text-2xl font-bold text-white">Mix<span className="text-violet-500">Mint</span></Link>
            <nav className="hidden md:flex items-center gap-6">
              {NAV_LINKS.map(link => (
                <Link 
                  key={link.href} 
                  href={link.href} 
                  className={cn(
                    "text-sm font-medium transition-colors",
                    pathname === link.href ? "text-violet-400" : "text-zinc-400 hover:text-white"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            {user ? (
              <div className="relative group">
                <Button variant="ghost" size="sm" className="flex items-center gap-2">
                   <User size={16} />
                   <span className="hidden sm:inline">{user.email}</span>
                </Button>
                <div className="absolute top-full right-0 mt-2 w-48 bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto">
                    <div className="py-1">
                       <Link href="/my-collection" className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"><Library size={14}/> My Collection</Link>
                       {user.role === 'dj' && (
                         <Link href="/dashboard" className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"><BarChart size={14}/> DJ Dashboard</Link>
                       )}
                       {user.role === 'admin' && (
                         <Link href="/admin/dj-approvals" className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"> <Settings size={14}/> Admin Panel</Link>
                       )}
                       <button onClick={signOut} className="flex items-center gap-2 w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-zinc-700">
                           <LogOut size={14} />
                           Sign Out
                       </button>
                    </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/auth/login">
                  <Button variant="ghost" size="sm">Log In</Button>
                </Link>
                <Link href="/auth/signup">
                  <Button size="sm">Sign Up</Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.header>
  );
}
