
"use client";

import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { Button } from "@/components/ui/Button";
import {
  LogOut,
  User,
  Search,
  Bell,
  Upload,
  Sparkles,
  ChevronDown,
  BarChart,
  Settings,
  Library,
  ShieldAlert
} from "lucide-react";
import { motion } from "framer-motion";
import { usePathname } from 'next/navigation';
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";

export function Navbar() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState("");
  const [userPoints, setUserPoints] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    if (user) {
      fetchUserPoints();
    }
  }, [user]);

  async function fetchUserPoints() {
    const { data } = await supabase
      .from('points')
      .select('balance')
      .eq('profile_id', user?.id)
      .single();

    if (data) setUserPoints(data.balance);
  }

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="sticky top-4 z-50 md:ml-60"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14 glass rounded-2xl px-4">

          {/* Search Bar (Centered) */}
          <div className="flex-1 max-w-md mx-auto">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                placeholder="Search tracks, DJs, albums..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-zinc-500 
                         focus:outline-none focus:ring-2 focus:ring-purple-primary focus:border-transparent
                         transition-all duration-200"
              />
            </div>
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-3">
            {user ? (
              <>
                {/* Upload Button (DJ only) */}
                {user.role === 'dj' && (
                  <Link href="/dashboard/upload">
                    <Button size="sm" className="btn-mint flex items-center gap-2 !py-2 !px-4">
                      <Upload size={14} />
                      <span className="hidden sm:inline">Upload</span>
                    </Button>
                  </Link>
                )}

                {/* Notifications */}
                <button className="relative p-2 rounded-lg hover:bg-white/10 transition-colors">
                  <Bell size={18} className="text-zinc-400" />
                  <span className="absolute top-1 right-1 w-2 h-2 bg-mint-accent rounded-full animate-pulse" />
                </button>

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowDropdown(!showDropdown)}
                    className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/10 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-purple flex items-center justify-center">
                      <User size={14} className="text-white" />
                    </div>

                    {/* Points Badge */}
                    {userPoints > 0 && (
                      <div className="hidden sm:flex items-center gap-1 bg-gold/20 text-gold px-2 py-0.5 rounded-full">
                        <Sparkles size={12} />
                        <span className="text-xs font-accent font-semibold">{userPoints}</span>
                      </div>
                    )}

                    <ChevronDown size={14} className="text-zinc-500" />
                  </button>

                  {/* Dropdown */}
                  {showDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute top-full right-0 mt-2 w-56 bg-surface-dark border border-white/10 rounded-xl shadow-glass overflow-hidden"
                    >
                      <div className="p-3 border-b border-white/5">
                        <p className="text-sm text-white font-medium truncate">{user.email}</p>
                        <p className="text-xs text-zinc-500 capitalize">{user.role}</p>
                      </div>
                      <div className="py-1">
                        <Link
                          href="/my-collection"
                          className="flex items-center gap-3 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
                          onClick={() => setShowDropdown(false)}
                        >
                          <Library size={14} />
                          My Collection
                        </Link>
                        {user.role === 'dj' && (
                          <Link
                            href="/dashboard"
                            className="flex items-center gap-3 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
                            onClick={() => setShowDropdown(false)}
                          >
                            <BarChart size={14} />
                            DJ Dashboard
                          </Link>
                        )}
                        {user.role === 'admin' && (
                          <>
                            <Link
                              href="/admin/dj-approvals"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
                              onClick={() => setShowDropdown(false)}
                            >
                              <Settings size={14} />
                              Admin Panel
                            </Link>
                            <Link
                              href="/admin/audit"
                              className="flex items-center gap-3 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5 transition-colors"
                              onClick={() => setShowDropdown(false)}
                            >
                              <ShieldAlert size={14} />
                              Audit Logs
                            </Link>
                          </>
                        )}
                      </div>
                      <div className="border-t border-white/5">
                        <button
                          onClick={() => { signOut(); setShowDropdown(false); }}
                          className="flex items-center gap-3 w-full px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                        >
                          <LogOut size={14} />
                          Sign Out
                        </button>
                      </div>
                    </motion.div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/auth/login">
                  <Button variant="ghost" size="sm">Log In</Button>
                </Link>
                <Link href="/auth/signup">
                  <Button size="sm" className="btn-primary !py-2 !px-4">Sign Up</Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.header>
  );
}
