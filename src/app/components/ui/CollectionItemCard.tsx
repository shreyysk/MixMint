'use client';

import Link from 'next/link';
import { Music, Package, Download, Loader2 } from 'lucide-react';
import { cn } from '@/app/lib/utils';
import { Button } from './Button';

interface CollectionItemCardProps {
  item: {
    id: string;
    title: string;
    type: 'track' | 'album';
    djName?: string;
    djSlug?: string;
  };
  onDownload: (itemType: 'track' | 'album', itemId: string) => void;
  isLoading: boolean;
}

export function CollectionItemCard({ item, onDownload, isLoading }: CollectionItemCardProps) {

  const handleDownload = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDownload(item.type, item.id);
  }

  const cardContent = (
    <>
      <div className="flex justify-between items-start">
        <div className='flex-grow'>
          <h3 className="text-lg font-bold text-white mb-2 line-clamp-2 leading-snug pr-4">
            {item.title}
          </h3>
          {item.djName && item.djSlug && (
            <Link href={`/dj/${item.djSlug}`} className="text-sm text-zinc-400 hover:text-violet-400 transition-colors line-clamp-1">
              by {item.djName}
            </Link>
          )}
        </div>
        
        {item.type === 'track' ? (
          <Music className="h-5 w-5 text-zinc-500 flex-shrink-0" />
        ) : (
          <Package className="h-5 w-5 text-zinc-500 flex-shrink-0" />
        )}
      </div>

      <div className="mt-auto pt-4 flex items-center justify-between border-t border-zinc-800/60">
        <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
            {item.type === 'track' ? 'Track' : 'Album'}
        </span>
        <Button 
            onClick={handleDownload}
            size="sm"
            variant="secondary"
            disabled={isLoading}
        >
            {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
                <Download className="h-4 w-4" />
            )}
            <span className="ml-2">Download</span>
        </Button>
      </div>
    </>
  );

  if (isLoading) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 h-full flex flex-col justify-between animate-pulse">
            <div>
                <div className="w-3/4 h-6 bg-zinc-800 rounded-md mb-3"></div>
                <div className="w-1/2 h-4 bg-zinc-800 rounded-md"></div>
            </div>
            <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60">
                <div className="w-1/4 h-4 bg-zinc-800 rounded-md"></div>
                <div className="w-24 h-9 bg-zinc-800 rounded-md"></div>
            </div>
        </div>
    );
  }

  return (
    <div 
        className={cn("group bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden h-full flex flex-col transition-all duration-300 hover:border-violet-500/50 hover:shadow-lg hover:shadow-violet-500/10 hover:-translate-y-1 p-4")}
        data-testid={`collection-item-${item.id}`}
    >
       {cardContent}
    </div>
  );
}
