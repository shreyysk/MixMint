'use client';

import React from 'react';
import Link from 'next/link';

const Footer = () => {
  return (
    <footer className="bg-mint-dark/50 p-4 mt-20 text-center text-sm text-mint-accent">
      <div className="flex justify-center space-x-4">
        <Link href="/legal/terms-of-service" className="hover:text-white">Terms of Service</Link>
        <Link href="/legal/privacy-policy" className="hover:text-white">Privacy Policy</Link>
        <Link href="/legal/refund-policy" className="hover:text-white">Refund Policy</Link>
      </div>
      <p className="mt-4">© 2024 MixMint. All rights reserved.</p>
    </footer>
  );
};

export default Footer;
