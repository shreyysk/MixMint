import * as React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'success' | 'amber';
    size?: 'sm' | 'md' | 'lg' | 'icon';
    loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', loading = false, children, disabled, ...props }, ref) => {
        const variants = {
            primary: "bg-gradient-to-br from-violet-600 to-violet-700 text-white hover:from-violet-500 hover:to-violet-600 shadow-[0_4px_24px_rgba(124,58,237,0.3)] hover:shadow-[0_6px_32px_rgba(124,58,237,0.45)] hover:-translate-y-0.5",
            secondary: "bg-gradient-to-br from-zinc-800 to-zinc-900 text-zinc-100 hover:from-zinc-700 hover:to-zinc-800 border border-zinc-700/80 hover:border-zinc-600 shadow-lg hover:shadow-xl hover:-translate-y-0.5",
            outline: "border-2 border-zinc-700/80 text-zinc-300 hover:bg-zinc-800/80 hover:text-white hover:border-zinc-600 bg-zinc-900/40 backdrop-blur-sm hover:-translate-y-0.5 shadow-sm hover:shadow-md",
            ghost: "text-zinc-400 hover:text-white hover:bg-zinc-800/60 hover:-translate-y-0.5",
            success: "bg-gradient-to-br from-emerald-600 to-emerald-700 text-white hover:from-emerald-500 hover:to-emerald-600 shadow-[0_4px_24px_rgba(16,185,129,0.3)] hover:shadow-[0_6px_32px_rgba(16,185,129,0.45)] hover:-translate-y-0.5",
            amber: "bg-gradient-to-br from-amber-600 to-amber-700 text-white hover:from-amber-500 hover:to-amber-600 shadow-[0_4px_24px_rgba(245,158,11,0.3)] hover:shadow-[0_6px_32px_rgba(245,158,11,0.45)] hover:-translate-y-0.5",
        };

        const sizes = {
            sm: "h-9 px-4 text-xs gap-2",
            md: "h-11 px-6 text-sm gap-2.5",
            lg: "h-14 px-8 text-base gap-3",
            icon: "h-10 w-10 flex items-center justify-center",
        };

        return (
            <button
                className={cn(
                    "inline-flex items-center justify-center rounded-xl font-bold transition-all duration-300 active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none disabled:hover:translate-y-0 tracking-wide relative overflow-hidden",
                    variants[variant],
                    sizes[size],
                    loading && "pointer-events-none",
                    className
                )}
                ref={ref}
                disabled={disabled || loading}
                {...props}
            >
                {/* Shine effect on hover */}
                <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-500">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                </div>

                {/* Content */}
                <span className={cn(
                    "relative z-10 flex items-center gap-2",
                    loading && "opacity-0"
                )}>
                    {children}
                </span>

                {/* Loading spinner */}
                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="animate-spin" size={size === 'sm' ? 16 : size === 'lg' ? 20 : 18} />
                    </div>
                )}
            </button>
        );
    }
);
Button.displayName = "Button";

export { Button };
