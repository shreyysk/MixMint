export function AlbumCardSkeleton() {
    return (
        <div className="relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60">
            {/* Content */}
            <div className="relative p-6">
                {/* Top Row: Icon + Download */}
                <div className="flex items-start justify-between mb-6">
                    <div className="w-14 h-14 rounded-xl skeleton" />
                    <div className="w-9 h-9 rounded-lg skeleton" />
                </div>

                {/* Album Info */}
                <div className="space-y-2.5 mb-5">
                    <div className="h-6 w-3/4 rounded skeleton" />
                    <div className="h-4 w-1/2 rounded skeleton" />
                    <div className="h-4 w-full rounded skeleton" />
                </div>

                {/* File Info Badge */}
                <div className="h-7 w-32 rounded-lg skeleton mb-5" />

                {/* Bottom CTA */}
                <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60">
                    <div className="h-3 w-20 rounded skeleton" />
                    <div className="w-9 h-9 rounded-full skeleton" />
                </div>
            </div>
        </div>
    );
}
