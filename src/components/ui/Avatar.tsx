import * as React from "react"
import { cn } from "@/lib/utils"

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
    src?: string | null;
    fallback: string;
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
    ({ className, src, fallback, ...props }, ref) => {
        const [error, setError] = React.useState(false);

        return (
            <div
                ref={ref}
                className={cn(
                    "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-zinc-800",
                    className
                )}
                {...props}
            >
                {src && !error ? (
                    <img
                        src={src}
                        className="aspect-square h-full w-full object-cover"
                        onError={() => setError(true)}
                        alt="avatar"
                    />
                ) : (
                    <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-xs font-bold text-zinc-300">
                        {fallback}
                    </div>
                )}
            </div>
        )
    }
)
Avatar.displayName = "Avatar"

export { Avatar }
