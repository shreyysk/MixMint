
import { Skeleton } from "./Skeleton";

export function TrackCardSkeleton() {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden h-full flex flex-col p-4">
            <div className="flex justify-between items-start mb-4">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-5 w-5 rounded-full" />
            </div>
            <Skeleton className="h-4 w-1/2 mb-8" />
            <div className="mt-auto pt-4 border-t border-zinc-800/60 flex items-center justify-between">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-8 w-24 rounded-lg" />
            </div>
        </div>
    );
}
