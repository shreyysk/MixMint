
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/Skeleton";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
    icon: LucideIcon;
    title: string;
    value: string;
    loading: boolean;
}

export function StatCard({ icon: Icon, title, value, loading }: StatCardProps) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-zinc-400">{title}</CardTitle>
                <Icon className="h-4 w-4 text-zinc-500" />
            </CardHeader>
            <CardContent>
                {loading ? (
                    <Skeleton className="h-8 w-1/2" />
                ) : (
                    <div className="text-2xl font-bold text-white">{value}</div>
                )}
            </CardContent>
        </Card>
    )
}
