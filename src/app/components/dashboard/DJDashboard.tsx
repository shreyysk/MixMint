
"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { SalesChart } from "@/app/components/dashboard/SalesChart";
import { TrackManager } from "@/app/components/dashboard/TrackManager";
import { AlbumManager } from "@/app/components/dashboard/AlbumManager";
import { StatCard } from "@/app/components/dashboard/StatCard";
import { DollarSign, Users, Music, Package, Upload } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import Link from "next/link";

interface Sale {
    created_at: string;
    price: number;
}

export function DJDashboard() {
    const { user } = useAuth();
    const [totalRevenue, setTotalRevenue] = useState(0);
    const [totalSales, setTotalSales] = useState(0);
    const [totalSubscribers, setTotalSubscribers] = useState(0);
    const [salesData, setSalesData] = useState<Sale[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchDashboardData();
        }
    }, [user]);

    async function fetchDashboardData() {
        setLoading(true);

        // Fetch DJ profile to get the correct dj_id
        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (djError || !djProfile) {
            console.error('Error fetching DJ profile:', djError);
            setLoading(false);
            return;
        }

        const djId = djProfile.id;

        const { data: sales, error: salesError } = await supabase
            .from("sales")
            .select("created_at, price")
            .eq("dj_id", djId);

        if (salesError) {
            console.error("Error fetching sales data:", salesError);
        } else if (sales) {
            const total = sales.reduce((acc, sale) => acc + sale.price, 0);
            setTotalRevenue(total);
            setTotalSales(sales.length);
            setSalesData(sales);
        }

        // Mock data for subscribers for now
        setTotalSubscribers(0);

        setLoading(false);
    }

    return (
        <div className="min-h-screen pb-24">
            <div className="px-6 md:px-12">
                <div className="max-w-7xl mx-auto">
                    <div className="flex justify-between items-center mb-10">
                        <h1 className="text-4xl md:text-5xl font-bold text-white">DJ Dashboard</h1>
                        <div className="flex gap-4">
                            <Link href="/dashboard/upload-track">
                                <Button><Upload size={16} className="mr-2"/> Upload Track</Button>
                            </Link>
                            <Link href="/dashboard/create-album">
                                <Button variant="outline">Create Album</Button>
                            </Link>
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
                        <StatCard icon={DollarSign} title="Total Revenue" value={`$${totalRevenue.toFixed(2)}`} loading={loading} />
                        <StatCard icon={Music} title="Total Sales" value={totalSales.toString()} loading={loading} />
                        <StatCard icon={Users} title="Subscribers" value={totalSubscribers.toString()} loading={loading} />
                    </div>

                    {/* Sales Chart */}
                    <div className="mb-10">
                        <h2 className="text-2xl font-bold text-white mb-6">Sales Analytics</h2>
                        <SalesChart salesData={salesData} loading={loading} />
                    </div>

                    {/* Track Manager */}
                    <div className="mb-10">
                        <h2 className="text-2xl font-bold text-white mb-6">Manage Tracks</h2>
                        <TrackManager />
                    </div>

                    {/* Album Manager */}
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-6">Manage Albums</h2>
                        <AlbumManager />
                    </div>
                </div>
            </div>
        </div>
    );
}
