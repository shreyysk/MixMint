import React from "react";
import Link from "next/link";
import { Music, Package, Download } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import { AccessBadge } from "@/app/components/ui/AccessBadge";

interface DownloadCardProps {
    id: string;
    title: string;
    djName: string;
    djSlug: string;
    type: 'track' | 'zip';
    accessType: 'purchased' | 'subscribed';
    onDownload: (id: string, type: string) => void;
    downloading?: boolean;
}

export function DownloadCard({
    id,
    title,
    djName,
    djSlug,
    type,
    accessType,
    onDownload,
    downloading = false,
}: DownloadCardProps) {
    const Icon = type === 'track' ? Music : Package;
    const typeLabel = type === 'track' ? 'Track' : 'Album Pack';

    return (
        <div className="group relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60 hover:border-violet-500/40 transition-all duration-300 p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl ${type === 'track' ? 'bg-violet-600/20 border-violet-500/30' : 'bg-amber-600/20 border-amber-500/30'} border flex items-center justify-center shrink-0`}>
                    <Icon className={type === 'track' ? 'text-violet-400' : 'text-amber-400'} size={20} />
                </div>

                {/* Access Badge */}
                <AccessBadge variant={accessType === 'purchased' ? 'owned' : 'subscribed'} />
            </div>

            {/* Content */}
            <div className="mb-4">
                <h3 className="text-lg font-bold text-white mb-2 line-clamp-2 leading-tight">
                    {title}
                </h3>

                <Link
                    href={`/dj/${djSlug}`}
                    className="text-sm text-zinc-500 hover:text-violet-400 transition-colors font-semibold inline-block mb-3"
                >
                    by {djName}
                </Link>

                <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-zinc-800/60 text-zinc-400 text-xs font-semibold uppercase tracking-wide">
                        {typeLabel}
                    </span>
                </div>
            </div>

            {/* Download Button */}
            <Button
                onClick={() => onDownload(id, type)}
                variant="primary"
                size="sm"
                loading={downloading}
                className="w-full"
            >
                <Download size={16} />
                Download
            </Button>
        </div>
    );
}
