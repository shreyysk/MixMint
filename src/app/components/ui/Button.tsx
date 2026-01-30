import * as React from "react";
import { cn } from "@/app/lib/utils";

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
    size?: 'sm' | 'md' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
        const variants = {
            primary: "bg-violet-600 text-white hover:bg-violet-700 shadow-[0_0_20px_rgba(124,58,237,0.3)]",
            secondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
            outline: "border border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white hover:border-violet-500/50",
            ghost: "text-zinc-400 hover:text-white hover:bg-zinc-900",
        };

        const sizes = {
            sm: "h-9 px-4 text-xs",
            md: "h-11 px-6 text-sm",
            lg: "h-13 px-8 text-base",
            icon: "h-10 w-10 flex items-center justify-center",
        };

        return (
            <button
                className={cn(
                    "inline-flex items-center justify-center rounded-xl font-bold transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:pointer-events-none uppercase tracking-wider",
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
