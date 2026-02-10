'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Compass, Library, User } from 'lucide-react';

const navItems = [
    { href: '/', icon: Home, label: 'Home' },
    { href: '/explore', icon: Compass, label: 'Explore' },
    { href: '/my-collection', icon: Library, label: 'Library' },
    { href: '/profile', icon: User, label: 'Profile' }
];

export default function BottomNav() {
    const pathname = usePathname();

    return (
        <nav className="fixed bottom-0 left-0 right-0 z-50 bg-black/95 backdrop-blur-lg border-t border-white/10 md:hidden">
            <div className="flex items-center justify-around h-16 px-2">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`
                flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-lg
                transition-all duration-200 min-w-[64px]
                ${isActive
                                    ? 'text-purple-400 bg-purple-500/10'
                                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                                }
              `}
                        >
                            <Icon className={`w-5 h-5 ${isActive ? 'scale-110' : ''}`} />
                            <span className="text-xs font-medium">{item.label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
