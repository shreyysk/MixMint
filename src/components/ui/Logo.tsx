'use client';

import Link from 'next/link';
import { Music, Disc } from 'lucide-react';

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 text-white">
        <div className='w-8 h-8 bg-violet-600 rounded-full flex items-center justify-center'>
            <Disc className='h-5 w-5' />
        </div>
      <span className="text-lg font-bold tracking-tight">MixMint</span>
    </Link>
  );
}
