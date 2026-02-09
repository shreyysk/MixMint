
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useAuth } from "@/lib/AuthContext";
import { SalesChart } from "@/components/features/dashboard/SalesChart";
import { TrackManager } from "@/components/features/dashboard/TrackManager";
import { AlbumManager } from "@/components/features/dashboard/AlbumManager";
import { StatCard } from "@/components/features/dashboard/StatCard";
import { EarningsCard } from "@/components/features/dj/EarningsCard";
import { DollarSign, Users, Music, Package, Upload } from "lucide-react";
import { Button } from "@/components/ui/Button";
import Link from "next/link";

interface Purchase {
    created_at: string;
    price_paid: number;
    content_type: 'track' | 'zip';
}

export function DJDashboard() {
    const { user } = useAuth();
    const [stats, setStats] = useState({
        totalRevenue: 0,
        monthlyEarnings: 0,
        trackEarnings: 0,
        albumEarnings: 0,
        totalSales: 0,
        totalSubscribers: 0,
    });
    const [salesData, setSalesData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchDashboardData();
        }
    }, [user]);

    async function fetchDashboardData() {
        setLoading(true);
        try {
            // 1. Fetch DJ profile
            const { data: djProfile, error: djError } = await supabase
                .from('dj_profiles')
                .select('id')
                .eq('id', user.id) // Corrected: dj_profiles PK is profiles.id
                .single();

            if (djError || !djProfile) throw djError;

            // 2. Fetch Wallet for Lifetime Earnings (or just Current Balance)
            // Note: Ledger gives a better history, but wallet balance is the "Cash Out-able" amount.
            const { data: wallet } = await supabase
                .from('wallets')
                .select('balance')
                .eq('id', user.id)
                .single();

            // 3. Fetch Purchases for breakdown
            const { data: purchases, error: purchaseErr } = await supabase
                .from("purchases")
                .select("created_at, price_paid, content_type")
                .eq("seller_id", djProfile.id);

            if (purchaseErr) throw purchaseErr;

            // 4. Aggregate Stats
            const now = new Date();
            const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

            let monthly = 0;
            let tracks = 0;
            let albums = 0;

            purchases?.forEach(p => {
                const date = new Date(p.created_at);
                const price = Number(p.price_paid);

                if (date >= startOfMonth) monthly += price;
                if (p.content_type === 'track') tracks += price;
                if (p.content_type === 'zip') albums += price;
            });

            // 5. Fetch Subscriber count
            const { count: subscriberCount } = await supabase
                .from("dj_subscriptions")
                .select("*", { count: 'exact', head: true })
                .eq("dj_id", djProfile.id)
                .gt("expires_at", now.toISOString());

            setStats({
                totalRevenue: Number(wallet?.balance || 0),
                monthlyEarnings: monthly,
                trackEarnings: tracks,
                albumEarnings: albums,
                totalSales: purchases?.length || 0,
                totalSubscribers: subscriberCount || 0,
            });

            setSalesData(purchases?.map(p => ({
                created_at: p.created_at,
                price: Number(p.price_paid)
            })) || []);

        } catch (err) {
            console.error("Dashboard Load Failed:", err);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen pb-24 pt-20 bg-black text-white">
            <div className="px-6 md:px-12 max-w-7xl mx-auto">
                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
                    <div>
                        <h1 className="text-4xl md:text-5xl font-black font-display tracking-tight text-mint-studio uppercase">
                            Artist Dashboard
                        </h1>
                        <p className="text-zinc-500 mt-2 font-medium">Manage your content, fans, and earnings.</p>
                    </div>
                    <div className="flex gap-4 w-full md:w-auto">
                        <Link href="/dashboard/upload-track" className="flex-1">
                            <Button className="w-full bg-mint-studio text-black font-bold">
                                <Upload size={18} className="mr-2" /> Upload Track
                            </Button>
                        </Link>
                        <Link href="/dashboard/create-album" className="flex-1">
                            <Button variant="outline" className="w-full border-zinc-800 hover:bg-zinc-900 font-bold">
                                Create Album
                            </Button>
                        </Link>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
                    {/* Left: Earnings Visualization */}
                    <div className="lg:col-span-2 space-y-8">
                        <EarningsCard
                            totalEarnings={stats.totalRevenue}
                            monthlyEarnings={stats.monthlyEarnings}
                            trackEarnings={stats.trackEarnings}
                            albumEarnings={stats.albumEarnings}
                        />

                        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-3xl p-8 backdrop-blur-sm">
                            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                                <span className="w-2 h-2 bg-mint-studio rounded-full"></span>
                                Sales Analytics
                            </h2>
                            <SalesChart salesData={salesData} loading={loading} />
                        </div>
                    </div>

                    {/* Right: Quick Stats & Managers */}
                    <div className="space-y-8">
                        <div className="grid grid-cols-1 gap-4">
                            <StatCard icon={Music} title="Orders Delivered" value={stats.totalSales.toString()} loading={loading} />
                            <StatCard icon={Users} title="Active Fans" value={stats.totalSubscribers.toString()} loading={loading} />
                        </div>

                        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-3xl p-6 backdrop-blur-sm">
                            <h3 className="font-bold mb-4 text-zinc-400">Content Managers</h3>
                            <div className="space-y-4">
                                <TrackManager />
                                <div className="h-px bg-zinc-800/60"></div>
                                <AlbumManager />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
