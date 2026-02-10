'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    Award,
    Users,
    Gift,
    TrendingUp,
    Plus,
    Minus,
    Search,
    ArrowUpRight,
    RefreshCw,
    UserPlus
} from 'lucide-react';

interface UserPoints {
    user_id: string;
    email: string;
    points_balance: number;
    total_earned: number;
    referral_count: number;
}

export default function PointsManagementPage() {
    const [users, setUsers] = useState<UserPoints[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadPointsData();
    }, []);

    async function loadPointsData() {
        try {
            setLoading(true);
            // This joins profiles with their points and referral stats
            // Note: In real schema, points might be in a separate table like 'points_balances'
            const { data, error } = await supabase
                .from('profiles')
                .select('id, email, full_name');

            if (error) throw error;

            // Mocking points data as the schema might vary
            const mockData = (data || []).map(u => ({
                user_id: u.id,
                email: u.email || 'no-email',
                points_balance: Math.floor(Math.random() * 5000),
                total_earned: Math.floor(Math.random() * 10000),
                referral_count: Math.floor(Math.random() * 12)
            }));

            setUsers(mockData);
        } catch (err) {
            console.error('[LOAD_POINTS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    const filteredUsers = users.filter(u =>
        u.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-yellow-500/10 rounded-2xl border border-yellow-500/20 shadow-yellow-glow">
                            <Award className="w-8 h-8 text-yellow-500" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Points & Referrals</h1>
                            <p className="text-zinc-400">Manage user rewards, milestones, and referral tracking.</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <div className="relative group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-yellow-500 transition-colors" size={18} />
                            <input
                                type="text"
                                placeholder="Search users..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="bg-zinc-900 border border-zinc-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-yellow-500/50 transition-all w-full md:w-64"
                            />
                        </div>
                    </div>
                </div>

                {/* Global Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-yellow-500/10 rounded-xl">
                                <Gift className="w-6 h-6 text-yellow-500" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Total Points Issued</p>
                                <p className="text-2xl font-bold text-white">42,50,000</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-xl">
                                <UserPlus className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Successful Referrals</p>
                                <p className="text-2xl font-bold text-white">8,420</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-emerald-500/10 rounded-xl">
                                <TrendingUp className="w-6 h-6 text-emerald-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Points Redeemed (Today)</p>
                                <p className="text-2xl font-bold text-white">₹12,450</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* User List */}
                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-white">User Rewards Ledger</CardTitle>
                            <CardDescription>View and manage individual point balances.</CardDescription>
                        </div>
                        <Button
                            onClick={loadPointsData}
                            variant="ghost"
                            size="sm"
                            className="text-zinc-500 hover:text-white"
                        >
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 10 }).map((_, i) => (
                                    <div key={i} className="h-14 bg-zinc-900 rounded-xl" />
                                ))}
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-zinc-900 hover:bg-transparent">
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">User Email</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Current Balance</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Total Earned</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Referrals</TableHead>
                                        <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest">Manual Adjustment</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredUsers.map((u) => (
                                        <TableRow key={u.user_id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                            <TableCell>
                                                <p className="text-sm font-medium text-white group-hover:text-yellow-500 transition-colors lowercase">{u.email}</p>
                                            </TableCell>
                                            <TableCell className="text-center font-bold text-yellow-500">
                                                {u.points_balance.toLocaleString()}
                                            </TableCell>
                                            <TableCell className="text-center text-zinc-400 font-medium">
                                                {u.total_earned.toLocaleString()}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <div className="flex items-center justify-center gap-1.5">
                                                    <Users size={12} className="text-blue-400" />
                                                    <span className="text-xs font-bold text-white">{u.referral_count}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button size="sm" variant="ghost" className="text-emerald-500 hover:bg-emerald-500/10 rounded-lg">
                                                        <Plus size={14} />
                                                    </Button>
                                                    <Button size="sm" variant="ghost" className="text-red-500 hover:bg-red-500/10 rounded-lg">
                                                        <Minus size={14} />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
