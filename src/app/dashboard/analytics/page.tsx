'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { SalesChart } from '@/components/features/dashboard/SalesChart';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, Users, DollarSign, Music, Globe, ArrowUpRight } from 'lucide-react';

export default function DJAnalyticsPage() {
    const { user } = useAuth();
    const [stats, setStats] = useState({
        totalEarnings: 0,
        totalSales: 0,
        activeSubscribers: 0,
        topTrack: 'None',
        topGenre: 'None'
    });
    const [salesHistory, setSalesHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) loadAnalytics();
    }, [user]);

    async function loadAnalytics() {
        try {
            // Mocking for now since we need a large dataset for meaningful charts
            // In production, this would aggregate from purchases, subscriptions, and activity_feed
            setStats({
                totalEarnings: 12450.00,
                totalSales: 42,
                activeSubscribers: 15,
                topTrack: 'Midnight Anthem',
                topGenre: 'Techno'
            });

            // Mock data for charts
            setSalesHistory([
                { created_at: '2025-01-01', price: 299 },
                { created_at: '2025-02-01', price: 450 },
                { created_at: '2025-03-01', price: 800 },
                { created_at: '2025-04-01', price: 1200 },
            ]);
        } catch (err) {
            console.error('[LOAD_ANALYTICS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    const COLORS = ['#8B5CF6', '#EC4899', '#3B82F6', '#10B981'];

    return (
        <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-heading font-bold text-white">DJ Analytics</h1>
                    <p className="text-zinc-400">Real-time insights into your performance and audience.</p>
                </div>
                <div className="flex gap-3">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest">Live Updates</span>
                    </div>
                </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="bg-zinc-950/50 border-zinc-800 group hover:border-purple-500/50 transition-all">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between mb-2">
                            <div className="p-2 bg-purple-500/10 rounded-lg">
                                <DollarSign className="w-5 h-5 text-purple-400" />
                            </div>
                            <span className="text-[10px] font-black text-green-500 flex items-center gap-1 uppercase">
                                +12% <ArrowUpRight className="w-3 h-3" />
                            </span>
                        </div>
                        <h3 className="text-base font-medium text-zinc-400">Total Earnings</h3>
                        <p className="text-2xl font-bold text-white mt-1">₹{stats.totalEarnings.toLocaleString()}</p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950/50 border-zinc-800 group hover:border-blue-500/50 transition-all">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between mb-2">
                            <div className="p-2 bg-blue-500/10 rounded-lg">
                                <Users className="w-5 h-5 text-blue-400" />
                            </div>
                            <span className="text-[10px] font-black text-blue-500 flex items-center gap-1 uppercase">
                                +5 <ArrowUpRight className="w-3 h-3" />
                            </span>
                        </div>
                        <h3 className="text-base font-medium text-zinc-400">Subscribers</h3>
                        <p className="text-2xl font-bold text-white mt-1">{stats.activeSubscribers}</p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950/50 border-zinc-800 group hover:border-pink-500/50 transition-all">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between mb-2">
                            <div className="p-2 bg-pink-500/10 rounded-lg">
                                <Music className="w-5 h-5 text-pink-400" />
                            </div>
                        </div>
                        <h3 className="text-base font-medium text-zinc-400">Top Track</h3>
                        <p className="text-lg font-bold text-white mt-1 truncate">{stats.topTrack}</p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-950/50 border-zinc-800 group hover:border-yellow-500/50 transition-all">
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-between mb-2">
                            <div className="p-2 bg-yellow-500/10 rounded-lg">
                                <Globe className="w-5 h-5 text-yellow-400" />
                            </div>
                        </div>
                        <h3 className="text-base font-medium text-zinc-400">Primary Region</h3>
                        <p className="text-2xl font-bold text-white mt-1">India</p>
                    </CardContent>
                </Card>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <Card className="bg-zinc-950/50 border-zinc-800">
                        <CardHeader>
                            <CardTitle className="text-white">Earnings History</CardTitle>
                            <CardDescription>Monthly revenue breakdown from all sources.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <SalesChart salesData={salesHistory} loading={loading} />
                        </CardContent>
                    </Card>
                </div>

                <div className="space-y-8">
                    <Card className="bg-zinc-950/50 border-zinc-800 h-full">
                        <CardHeader>
                            <CardTitle className="text-white">Audience Mix</CardTitle>
                            <CardDescription>Breakdown by genre preference.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex justify-center pt-8">
                            <div className="w-full h-[300px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={[
                                        { name: 'Techno', value: 45 },
                                        { name: 'House', value: 30 },
                                        { name: 'EDM', value: 15 },
                                        { name: 'Other', value: 10 },
                                    ]} layout="vertical">
                                        <XAxis type="number" hide />
                                        <YAxis dataKey="name" type="category" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                                        <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} contentStyle={{ backgroundColor: '#18181B', border: '1px solid #3F3F46' }} />
                                        <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#8B5CF6">
                                            {[0, 1, 2, 3].map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
