'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  DollarSign,
  Users,
  Music,
  Download,
  Star,
  ShieldCheck,
  TrendingUp,
  Clock,
  Trash2,
  AlertCircle,
  Server,
  Search
} from 'lucide-react';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

export default function AdminPage() {
  const [metrics, setMetrics] = useState({
    totalRevenue: 0,
    activeDJs: 0,
    totalUsers: 0,
    totalTracks: 0,
    totalDownloads: 0,
    activeSubs: 0,
    pendingPayouts: 0,
  });
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    try {
      setLoading(true);

      // 1. Fetch Key Metrics (In aggregation)
      // Note: In production, these should be cached or pre-aggregated
      const { data: profiles } = await supabase.from('profiles').select('count', { count: 'exact' });
      const { data: djs } = await supabase.from('dj_profiles').select('count', { count: 'exact' });
      const { data: tracks } = await supabase.from('tracks').select('count', { count: 'exact' });
      const { data: purchases } = await supabase.from('purchases').select('amount_paid');

      const totalRevenue = (purchases || []).reduce((acc, p) => acc + p.amount_paid, 0);

      setMetrics({
        totalRevenue,
        activeDJs: djs?.length || 0,
        totalUsers: profiles?.length || 0,
        totalTracks: tracks?.length || 0,
        totalDownloads: 1240, // Mock for now
        activeSubs: 85, // Mock for now
        pendingPayouts: 12450.50, // Mock for now
      });

      // 2. Mock Trend Data
      setRevenueData([
        { name: 'Week 1', revenue: 4000 },
        { name: 'Week 2', revenue: 3000 },
        { name: 'Week 3', revenue: 6000 },
        { name: 'Week 4', revenue: 8500 },
      ]);

      // 3. Fetch Recent Activity
      const { data: activity } = await supabase
        .from('activity_feed')
        .select(`
                    *,
                    profiles (full_name)
                `)
        .order('created_at', { ascending: false })
        .limit(10);

      setRecentActivity(activity || []);

    } catch (err) {
      console.error('[ADMIN_DASHBOARD_ERROR]', err);
    } finally {
      setLoading(false);
    }
  }

  const StatCard = ({ title, value, icon: Icon, color, trend }: any) => (
    <Card className="bg-zinc-950/50 border-zinc-900 overflow-hidden relative group">
      <div className={`absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity`}>
        <Icon size={120} />
      </div>
      <CardContent className="pt-6 relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-2 rounded-xl bg-${color}-500/10 border border-${color}-500/20 shadow-${color}-glow`}>
            <Icon className={`w-5 h-5 text-${color}-400`} />
          </div>
          {trend && (
            <span className={`text-[10px] font-black ${trend > 0 ? 'text-green-500' : 'text-red-500'} uppercase tracking-widest`}>
              {trend > 0 ? '+' : ''}{trend}%
            </span>
          )}
        </div>
        <h3 className="text-zinc-500 text-xs font-bold uppercase tracking-widest">{title}</h3>
        <p className="text-2xl font-bold text-white mt-1">
          {title.includes('Revenue') || title.includes('Payouts') ? `₹${value.toLocaleString()}` : value.toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 space-y-8 animate-in fade-in duration-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-heading font-bold text-white">Platform Overview</h1>
            <p className="text-zinc-400">Real-time health and performance metrics for MixMint.</p>
          </div>
          <div className="flex gap-3">
            <div className="flex items-center gap-2 bg-zinc-900/50 border border-emerald-500/20 px-4 py-2 rounded-xl">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">System Healthy</span>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard title="Total Revenue" value={metrics.totalRevenue} icon={DollarSign} color="purple" trend={12} />
          <StatCard title="Active DJs" value={metrics.activeDJs} icon={Music} color="blue" trend={5} />
          <StatCard title="Total Users" value={metrics.totalUsers} icon={Users} color="pink" />
          <StatCard title="Total Tracks" value={metrics.totalTracks} icon={Search} color="yellow" />
        </div>

        {/* Charts and Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Revenue Chart */}
          <Card className="lg:col-span-2 bg-zinc-950/50 border-zinc-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-400" />
                Revenue Trends
              </CardTitle>
              <CardDescription>Platform growth over the last 30 days.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={revenueData}>
                    <defs>
                      <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="name" stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} />
                    <YAxis stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} tickFormatter={(val) => `₹${val / 1000}k`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#09090b', border: '1px solid #27272a', borderRadius: '12px' }}
                      itemStyle={{ color: '#8B5CF6', fontWeight: 'bold' }}
                    />
                    <Area type="monotone" dataKey="revenue" stroke="#8B5CF6" fillOpacity={1} fill="url(#colorRev)" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="bg-zinc-950/50 border-zinc-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-400" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex gap-4 animate-pulse">
                      <div className="w-8 h-8 rounded-full bg-zinc-900" />
                      <div className="flex-1 space-y-2">
                        <div className="h-3 bg-zinc-900 rounded w-3/4" />
                        <div className="h-2 bg-zinc-900 rounded w-1/4" />
                      </div>
                    </div>
                  ))
                ) : recentActivity.length > 0 ? (
                  recentActivity.map((activity) => (
                    <div key={activity.id} className="flex gap-4">
                      <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0">
                        <ShieldCheck className="w-4 h-4 text-purple-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-zinc-300">
                          <span className="font-bold text-white">{activity.profiles?.full_name}</span>
                          {activity.action_type === 'release' ? ' uploaded a new track ' : ' commented on '}
                          <span className="text-purple-400 font-medium">{activity.metadata?.title}</span>
                        </p>
                        <p className="text-[10px] text-zinc-500 mt-1 uppercase font-bold tracking-tighter">
                          {new Date(activity.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-zinc-600 text-sm py-8">No recent activity.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Secondary Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-zinc-900/30 border-zinc-900">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
                <Server className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <h4 className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Bucket Status</h4>
                <p className="text-white font-bold">R2 Storage Active</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/30 border-zinc-900">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20">
                <Star className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h4 className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Active Subs</h4>
                <p className="text-white font-bold">{metrics.activeSubs} Pro Users</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/30 border-zinc-900">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-orange-500/10 rounded-2xl border border-orange-500/20">
                <AlertCircle className="w-6 h-6 text-orange-400" />
              </div>
              <div>
                <h4 className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Pending Payouts</h4>
                <p className="text-white font-bold">₹{metrics.pendingPayouts.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </RequireRole>
  );
}
