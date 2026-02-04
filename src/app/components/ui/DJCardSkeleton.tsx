export function DJCardSkeleton() {
    return (
        <div className="relative block overflow-hidden rounded-2xl bg-zinc-900/60 backdrop-blur-sm border border-zinc-800/60">
            {/* Image Container Skeleton */}
            <div className="aspect-[4/5] relative overflow-hidden">
                <div className="w-full h-full skeleton" />
                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/70 to-transparent" />
            </div>

            {/* Content Overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
                {/* Genre Tags Skeleton */}
                <div className="flex flex-wrap gap-2 mb-4">
                    <div className="h-6 w-16 rounded-lg skeleton" />
                    <div className="h-6 w-20 rounded-lg skeleton" />
                </div>

                {/* DJ Name + CTA Row */}
                <div className="flex items-end justify-between gap-4">
                    <div className="h-7 w-32 rounded skeleton" />
                    <div className="shrink-0 w-11 h-11 rounded-full skeleton" />
                </div>
            </div>
        </div>
    );
}
