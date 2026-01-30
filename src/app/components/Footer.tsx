import Link from "next/link";
import { Headphones, Twitter, Instagram, Github } from "lucide-react";

export function Footer() {
    return (
        <footer className="bg-black border-t border-zinc-900 py-16 px-6 md:px-12">
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 text-center md:text-left">
                <div className="col-span-1 md:col-span-1 flex flex-col items-center md:items-start">
                    <Link href="/" className="flex items-center gap-2 mb-6 group">
                        <div className="w-8 h-8 bg-violet-600 rounded flex items-center justify-center">
                            <Headphones className="text-white" size={18} />
                        </div>
                        <span className="text-lg font-black tracking-tighter text-white uppercase italic">MixMint</span>
                    </Link>
                    <p className="text-zinc-500 text-sm leading-relaxed mb-6">
                        MixMint — Home of DJ Releases. No streaming, just pure audio ownership.
                    </p>
                    <div className="flex gap-4">
                        <Twitter className="text-zinc-600 hover:text-white cursor-pointer transition-colors" size={20} />
                        <Instagram className="text-zinc-600 hover:text-white cursor-pointer transition-colors" size={20} />
                        <Github className="text-zinc-600 hover:text-white cursor-pointer transition-colors" size={20} />
                    </div>
                </div>

                <div>
                    <h4 className="text-white font-bold text-xs uppercase tracking-widest mb-6">Music</h4>
                    <ul className="space-y-4 text-sm text-zinc-500 font-bold">
                        <li><Link href="/explore" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Explore DJs</Link></li>
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Latest Drops</Link></li>
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Genres</Link></li>
                    </ul>
                </div>

                <div>
                    <h4 className="text-white font-bold text-xs uppercase tracking-widest mb-6">Platform</h4>
                    <ul className="space-y-4 text-sm text-zinc-500 font-bold">
                        <li><Link href="/pricing" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Pricing</Link></li>
                        <li><Link href="/become-dj" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Become a DJ</Link></li>
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Artist Tools</Link></li>
                    </ul>
                </div>

                <div>
                    <h4 className="text-white font-bold text-xs uppercase tracking-widest mb-6">Legal</h4>
                    <ul className="space-y-4 text-sm text-zinc-500 font-bold">
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Privacy Policy</Link></li>
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Terms</Link></li>
                        <li><Link href="#" className="hover:text-violet-500 transition-colors uppercase tracking-tight">Copyright</Link></li>
                    </ul>
                </div>
            </div>

            <div className="max-w-7xl mx-auto mt-20 pt-8 border-t border-zinc-900 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] text-zinc-600 uppercase tracking-widest font-black">
                <p>&copy; 2024 MixMint — Demo UI Only</p>
                <p>Built for the nightlife</p>
            </div>
        </footer>
    );
}
