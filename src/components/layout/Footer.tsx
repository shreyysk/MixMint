'use client';

import React from 'react';
import Link from 'next/link';

const Footer = () => {
  return (
    <footer className="bg-zinc-950/50 backdrop-blur-xl border-t border-white/5 py-20 mt-24">
      <div className="max-w-7xl mx-auto px-6 md:px-12 grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="col-span-1 md:col-span-2 space-y-6">
          <h2 className="text-3xl font-black text-white italic tracking-tighter uppercase">Mix<span className="text-gradient-mint">Mint</span></h2>
          <p className="text-zinc-500 max-w-sm font-bold leading-relaxed">
            The premium direct-to-fan marketplace for DJs and producers.
            Own your content, grow your tribe.
          </p>
        </div>

        <div>
          <h3 className="text-zinc-300 text-[10px] font-black uppercase tracking-[0.2em] mb-6">Platform</h3>
          <ul className="space-y-4 text-sm font-bold text-zinc-500">
            <li><Link href="/explore" className="hover:text-white transition-colors">Explore</Link></li>
            <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></li>
            <li><Link href="/contact" className="hover:text-white transition-colors">Contact Support</Link></li>
          </ul>
        </div>

        <div>
          <h3 className="text-zinc-300 text-[10px] font-black uppercase tracking-[0.2em] mb-6">Legal</h3>
          <ul className="space-y-4 text-sm font-bold text-zinc-500">
            <li><Link href="/legal/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
            <li><Link href="/legal/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
            <li><Link href="/legal/refund-policy" className="hover:text-white transition-colors">Refund Policy</Link></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-12 mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-zinc-600 text-xs font-bold">© {new Date().getFullYear()} MixMint. All rights reserved.</p>
        <div className="flex gap-6">
          {/* Social icons could go here */}
        </div>
      </div>
    </footer>
  );
};

export default Footer;
