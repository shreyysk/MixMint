import Link from "next/link";
import { Headphones, Twitter, Instagram, Github } from "lucide-react";

export function Footer() {
    return (
        <footer className="bg-zinc-950 border-t border-zinc-900/80 py-16 px-6 md:px-12">
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 text-center md:text-left">
                {/* Brand Column */}
                <div className="col-span-1 md:col-span-1 flex flex-col items-center md:items-start">
                    <Link href="/" className="flex items-center gap-2.5 mb-6 group">
                        <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-violet-700 rounded-lg flex items-center justify-center">
                            <Headphones className="text-white" size={16} />
                        </div>
                        <span className="text-base font-bold tracking-tight text-white">MixMint</span>
                    </Link>
                    <p className="text-zinc-500 text-sm leading-relaxed mb-6">
                        Home of DJ Releases. No streaming, just pure audio ownership.
                    </p>
                    <div className="flex gap-3">
                        <a href="#" className="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                            <Twitter size={16} />
                        </a>
                        <a href="#" className="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                            <Instagram size={16} />
                        </a>
                        <a href="#" className="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-600 transition-all">
                            <Github size={16} />
                        </a>
                    </div>
                </div>

                {/* Music Links */}
                <div>
                    <h4 className="text-white font-semibold text-sm mb-6">Music</h4>
                    <ul className="space-y-3 text-sm">
                        <li><Link href="/explore" className="text-zinc-500 hover:text-violet-400 transition-colors">Explore DJs</Link></li>
                        <li><Link href="/tracks" className="text-zinc-500 hover:text-violet-400 transition-colors">Browse Tracks</Link></li>
                        <li><Link href="/albums" className="text-zinc-500 hover:text-violet-400 transition-colors">Album Packs</Link></li>
                    </ul>
                </div>

                {/* Platform Links */}
                <div>
                    <h4 className="text-white font-semibold text-sm mb-6">Platform</h4>
                    <ul className="space-y-3 text-sm">
                        <li><Link href="/pricing" className="text-zinc-500 hover:text-violet-400 transition-colors">Pricing</Link></li>
                        <li><Link href="/dj/apply" className="text-zinc-500 hover:text-violet-400 transition-colors">Become a DJ</Link></li>
                        <li><Link href="/dashboard" className="text-zinc-500 hover:text-violet-400 transition-colors">Dashboard</Link></li>
                    </ul>
                </div>

                {/* Legal Links */}
                <div>
                    <h4 className="text-white font-semibold text-sm mb-6">Legal</h4>
                    <ul className="space-y-3 text-sm">
                        <li><Link href="/legal/privacy" className="text-zinc-500 hover:text-violet-400 transition-colors">Privacy Policy</Link></li>
                        <li><Link href="/legal/terms" className="text-zinc-500 hover:text-violet-400 transition-colors">Terms of Service</Link></li>
                        <li><Link href="/legal/refund-policy" className="text-zinc-500 hover:text-violet-400 transition-colors">Refund Policy</Link></li>
                        <li><Link href="/legal/payment-disclaimer" className="text-zinc-500 hover:text-violet-400 transition-colors">Payment Info</Link></li>
                        <li><Link href="/contact" className="text-zinc-500 hover:text-violet-400 transition-colors">Contact Us</Link></li>
                    </ul>
                </div>
            </div>

            {/* Bottom Bar */}
            <div className="max-w-7xl mx-auto mt-16 pt-8 border-t border-zinc-800/60 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-zinc-600">
                <p>&copy; 2024 MixMint. All rights reserved.</p>
                <p className="text-zinc-700">Built for the nightlife</p>
            </div>
        </footer>
    );
}
