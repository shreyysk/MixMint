
"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/Skeleton";

interface Sale {
    created_at: string;
    price: number;
}

interface SalesChartProps {
    salesData: Sale[];
    loading: boolean;
}

export function SalesChart({ salesData, loading }: SalesChartProps) {

    const processData = (sales: Sale[]) => {
        const monthlySales = sales.reduce((acc, sale) => {
            const month = new Date(sale.created_at).toLocaleString('default', { month: 'short' });
            acc[month] = (acc[month] || 0) + sale.price;
            return acc;
        }, {} as Record<string, number>);

        const chartData = Object.keys(monthlySales).map(month => ({
            name: month,
            total: monthlySales[month]
        }));

        return chartData;
    };

    const chartData = processData(salesData);

    if (loading) {
        return <Skeleton className="h-[350px] w-full" />
    }

    return (
        <Card>
            <CardContent className="pt-6">
                <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                        <Tooltip cursor={{ fill: 'rgba(139, 92, 246, 0.1)' }} contentStyle={{ backgroundColor: '#18181B', border: '1px solid #3F3F46' }} />
                        <Bar dataKey="total" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
