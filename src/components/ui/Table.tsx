import React from "react";
import { cn } from "@/lib/utils";

export const Table = ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className="w-full overflow-auto">
        <table className={cn("w-full caption-bottom text-sm", className)}>{children}</table>
    </div>
);

export const TableHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <thead className={cn("[&_tr]:border-b border-zinc-800", className)}>{children}</thead>
);

export const TableBody = ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <tbody className={cn("[&_tr:last-child]:border-0", className)}>{children}</tbody>
);

export const TableRow = ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <tr className={cn("border-b border-zinc-800 transition-colors hover:bg-zinc-900/50 data-[state=selected]:bg-muted", className)}>
        {children}
    </tr>
);

export const TableHead = ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <th className={cn("h-12 px-4 text-left align-middle font-medium text-zinc-400 [&:has([role=checkbox])]:pr-0", className)}>
        {children}
    </th>
);

export const TableCell = ({ children, className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className={cn("p-4 align-middle [&:has([role=checkbox])]:pr-0 text-zinc-300", className)} {...props}>
        {children}
    </td>
);
