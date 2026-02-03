import * as React from "react";
import { cn } from "@/app/lib/utils";

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'success' | 'amber';
    size?: 'sm' | 'md' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
        const variants = {
            primary: "bg-violet-600 text-white hover:bg-violet-500 shadow-[0_4px_20px_rgba(124,58,237,0.25)] hover:shadow-[0_4px_30px_rgba(124,58,237,0.4)]",
            secondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 border border-zinc-700",
            outline: "border border-zinc-700/80 text-zinc-300 hover:bg-zinc-800/60 hover:text-white hover:border-zinc-600 bg-zinc-900/40",
            ghost: "text-zinc-400 hover:text-white hover:bg-zinc-800/60",
            success: "bg-emerald-600 text-white hover:bg-emerald-500 shadow-[0_4px_20px_rgba(16,185,129,0.25)]",
            amber: "bg-amber-600 text-white hover:bg-amber-500 shadow-[0_4px_20px_rgba(245,158,11,0.25)]",
        };

        const sizes = {
            sm: "h-9 px-4 text-xs gap-2",
            md: "h-11 px-6 text-sm gap-2",
            lg: "h-14 px-8 text-sm gap-3",
            icon: "h-10 w-10 flex items-center justify-center",
        };

        return (
            <button
                className={cn(
                    "inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none tracking-wide",
                    variants[variant],
                    sizes[size],
                    className
                )}
                ref={ref}
                {...props}
            />
        );
    }
);
Button.displayName = "Button";

export { Button };
