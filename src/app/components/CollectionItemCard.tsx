
"use client";

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/app/components/ui/Card";
import { Button } from "@/app/components/ui/Button";
import { Download, Music, Package } from "lucide-react";
import Link from "next/link";

interface CollectionItem {
    id: string;
    title: string;
    item_type: 'track' | 'album';
    dj_profile?: {
        dj_name: string;
        slug: string;
    };
}

interface CollectionItemCardProps {
    item: CollectionItem;
    onDownload: (item: CollectionItem) => void;
}

export function CollectionItemCard({ item, onDownload }: CollectionItemCardProps) {
    const Icon = item.item_type === 'track' ? Music : Package;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-start justify-between">
                    <CardTitle className="line-clamp-2">{item.title}</CardTitle>
                    <Icon className="h-5 w-5 text-zinc-500 flex-shrink-0" />
                </div>
                {item.dj_profile && (
                    <Link href={`/djs/${item.dj_profile.slug}`} className="text-sm text-zinc-400 hover:text-violet-400 transition-colors">
                        by {item.dj_profile.dj_name}
                    </Link>
                )}
            </CardHeader>
            <CardFooter>
                 <Button 
                    variant="default"
                    size="sm"
                    className="w-full"
                    onClick={() => onDownload(item)} 
                    disabled={item.item_type === 'album'} // Disabling album downloads for now
                >
                    <Download className="mr-2 h-4 w-4" />
                    {item.item_type === 'album' ? 'Download (Coming Soon)' : 'Download'}
                </Button>
            </CardFooter>
        </Card>
    )
}
