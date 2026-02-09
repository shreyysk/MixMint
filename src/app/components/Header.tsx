'use client';

import Link from 'next/link';
import { useAuth } from '@/app/lib/AuthContext';
import { supabase } from '@/app/lib/supabaseClient';
import { Logo } from './ui/Logo';
import { Button } from './ui/Button';
import { usePathname } from 'next/navigation';
import { cn } from '@/app/lib/utils';

const NavLink = ({ href, children }: { href: string; children: React.ReactNode }) => {
    const pathname = usePathname();
    const isActive = pathname === href;

    return (
        <Link href={href} className={cn("px-3 py-2 rounded-md text-sm font-medium transition-colors", 
            isActive ? "text-white" : "text-zinc-400 hover:text-white
        )}>
            {children}
        </Link>
    )
}

export function Header() {
  const { user, loading } = useAuth();

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-black/50 backdrop-blur-lg border-b border-zinc-900">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between h-20">
          <div className="flex items-center gap-8">
            <Logo />
            <nav className='hidden md:flex items-center gap-4'>
                <NavLink href="/explore">Explore</NavLink>
                <NavLink href="/my-collection">My Collection</NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            {!loading && (
              user ? (
                <>
                  <Button onClick={handleLogout} variant="ghost" size="sm">
                    Logout
                  </Button>
                  <Link href="/dashboard">
                    <Button size="sm">Dashboard</Button>
                  </Link>
                </>
              ) : (
                <>
                    <Link href="/auth/login">
                        <Button variant="ghost" size="sm">
                            Log In
                        </Button>
                    </Link>
                    <Link href="/auth/signup">
                        <Button size="sm">
                            Sign Up
                        </Button>
                    </Link>
                </>
              )
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
