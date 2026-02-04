export function TrackCardSkeleton() {
    return (
        <div className="relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60">
            {/* Content */}
            <div className="relative p-6">
                {/* Top Row: Icon + Actions */}
                <div className="flex items-start justify-between mb-6">
                    <div className="w-14 h-14 rounded-xl skeleton" />
                    <div className="flex items-center gap-2">
                        <div className="w-9 h-9 rounded-lg skeleton" />
                    </div>
                </div>

                {/* Track Info */}
                <div className="space-y-2 mb-6">
                    <div className="h-6 w-3/4 rounded skeleton" />
                    <div className="h-4 w-1/2 rounded skeleton" />
                </div>

                {/* Bottom CTA */}
                <div className="flex items-center justify-between pt-4 border-t border-zinc-800/60">
                    <div className="h-3 w-24 rounded skeleton" />
                    <div className="w-9 h-9 rounded-full skeleton" />
                </div>
            </div>
        </div>
    );
}
