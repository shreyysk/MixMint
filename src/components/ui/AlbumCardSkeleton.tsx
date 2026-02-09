
import { Card, CardContent, CardFooter, CardHeader } from "./card";
import { Skeleton } from "./Skeleton";

export function AlbumCardSkeleton() {
    return (
        <Card className="overflow-hidden bg-zinc-900/50 border-zinc-800">
            <CardHeader className="p-0">
                <Skeleton className="h-48 w-full rounded-none bg-zinc-800" />
            </CardHeader>
            <CardContent className="p-4 space-y-3">
                <Skeleton className="h-6 w-3/4 bg-zinc-800" />
                <Skeleton className="h-4 w-1/2 bg-zinc-800" />
                <div className="flex justify-between items-center pt-2">
                    <Skeleton className="h-4 w-1/3 bg-zinc-800" />
                    <Skeleton className="h-4 w-1/4 bg-zinc-800" />
                </div>
            </CardContent>
            <CardFooter className="p-4 pt-0">
                <Skeleton className="h-10 w-full bg-zinc-800" />
            </CardFooter>
        </Card>
    );
}
