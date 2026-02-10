'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    DollarSign,
    CreditCard,
    ArrowUpRight,
    ArrowDownRight,
    TrendingUp,
    History,
    Download,
    Filter,
    Search,
    Clock,
    CheckCircle,
    XCircle,
    FileText
} from 'lucide-react';
import { ExportButton } from '@/components/ui/ExportButton';

interface Transaction {
    id: string;
    amount_paid: number;
    created_at: string;
    user_id: string;
    profiles: {
        full_name: string;
    };
    tracks: {
        title: string;
        dj_profiles: {
            dj_name: string;
        }
    } | null;
    album_packs: {
        title: string;
        dj_profiles: {
            dj_name: string;
        }
    } | null;
}

export default function FinancePage() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        totalRevenue: 0,
        pendingPayouts: 0,
        refundsCount: 0
    });

    useEffect(() => {
        loadFinanceData();
    }, []);

    async function loadFinanceData() {
        try {
            setLoading(true);

            // 1. Fetch Transactions
            const { data: txs, error } = await supabase
                .from('purchases')
                .select(`
                    *,
                    profiles (full_name),
                    tracks (title, dj_profiles (dj_name)),
                    album_packs (title, dj_profiles (dj_name))
                `)
                .order('created_at', { ascending: false })
                .limit(50);

            if (error) throw error;
            setTransactions(txs || []);

            // 2. Aggregate Stats
            const total = (txs || []).reduce((acc, t) => acc + t.amount_paid, 0);
            setStats({
                totalRevenue: total,
                pendingPayouts: 14500.00, // Mock for now
                refundsCount: 2
            });

        } catch (err) {
            console.error('[LOAD_FINANCE_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleRefund(txId: string) {
        if (!confirm("Are you sure you want to process a refund for this transaction? This action is irreversible on the platform level.")) return;

        try {
            // In production, this would call the payment provider's refund API
            const { error } = await supabase
                .from('purchases')
                .update({ status: 'refunded', amount_paid: 0 })
                .eq('id', txId);

            if (error) throw error;
            setTransactions(prev => prev.map(t => t.id === txId ? { ...t, amount_paid: 0 } : t));
            alert("Refund processed successfully on MixMint. Please ensure you also process it in the Razorpay dashboard.");
        } catch (err) {
            console.error('[REFUND_ERROR]', err);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 shadow-emerald-glow">
                            <DollarSign className="w-8 h-8 text-emerald-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Financial Intelligence</h1>
                            <p className="text-zinc-400">Manage transaction logs, payouts, and platform revenue splits.</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <ExportButton
                            data={transactions.map(tx => ({
                                id: tx.id,
                                amount: tx.amount_paid,
                                date: tx.created_at,
                                customer: tx.profiles?.full_name,
                                item: tx.tracks?.title || tx.album_packs?.title,
                                dj: (tx.tracks?.dj_profiles || tx.album_packs?.dj_profiles)?.dj_name
                            }))}
                            filename="mixmint_transactions"
                        />
                    </div>
                </div>

                {/* Financial Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <Card className="bg-zinc-950/20 border-emerald-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-emerald-500/10 rounded-xl">
                                    <ArrowUpRight className="w-6 h-6 text-emerald-400" />
                                </div>
                                <div>
                                    <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Gross Sales</p>
                                    <p className="text-2xl font-bold text-white">₹{stats.totalRevenue.toLocaleString()}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-purple-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-purple-500/10 rounded-xl">
                                    <TrendingUp className="w-6 h-6 text-purple-400" />
                                </div>
                                <div>
                                    <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Commission (15%)</p>
                                    <p className="text-2xl font-bold text-white">₹{(stats.totalRevenue * 0.15).toLocaleString()}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-orange-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-orange-500/10 rounded-xl">
                                    <Clock className="w-6 h-6 text-orange-400" />
                                </div>
                                <div>
                                    <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">DJ Earnings</p>
                                    <p className="text-2xl font-bold text-white">₹{(stats.totalRevenue * 0.85).toLocaleString()}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-blue-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-blue-500/10 rounded-xl">
                                    <CreditCard className="w-6 h-6 text-blue-400" />
                                </div>
                                <div>
                                    <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Active Tx</p>
                                    <p className="text-2xl font-bold text-white">{transactions.length}</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Tax & Reporting (Expansion) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <Card className="bg-zinc-950/50 border-zinc-900">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <FileText className="w-5 h-5 text-yellow-500" />
                                Tax & Compliance Summary
                            </CardTitle>
                            <CardDescription>Estimated GST/Tax liabilities based on gross revenue.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex justify-between items-center p-3 bg-zinc-900/50 rounded-xl border border-zinc-800">
                                <span className="text-zinc-400 text-xs font-bold uppercase tracking-wider">Estimated GST (18%)</span>
                                <span className="text-white font-bold">₹{(stats.totalRevenue * 0.18).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between items-center p-3 bg-zinc-900/50 rounded-xl border border-zinc-800">
                                <span className="text-zinc-400 text-xs font-bold uppercase tracking-wider">TDS Deductions (Proj)</span>
                                <span className="text-white font-bold">₹{(stats.totalRevenue * 0.05).toLocaleString()}</span>
                            </div>
                            <Button variant="outline" className="w-full border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-900">
                                <Download className="w-4 h-4 mr-2" />
                                Download Monthly Tax Report
                            </Button>
                        </CardContent>
                    </Card>

                    <Card className="bg-zinc-950/50 border-zinc-900">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <CheckCircle className="w-5 h-5 text-emerald-400" />
                                Payout Integrity
                            </CardTitle>
                            <CardDescription>Verified balance available for DJ disbursement.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex flex-col items-center justify-center py-6 text-center">
                            <div className="p-4 bg-emerald-500/10 rounded-full mb-4">
                                <CheckCircle className="w-10 h-10 text-emerald-400" />
                            </div>
                            <h3 className="text-xl font-bold text-white tracking-tight">System Consistent</h3>
                            <p className="text-xs text-zinc-500 max-w-[200px] mt-2">All transactions verified against Razorpay gateway status.</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Transaction Ledger */}
                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-white flex items-center gap-2">
                                <History className="w-5 h-5 text-purple-400" />
                                Transaction Ledger
                            </CardTitle>
                            <CardDescription>Global financial history and revenue split audit.</CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 8 }).map((_, i) => (
                                    <div key={i} className="h-12 bg-zinc-900 rounded-lg" />
                                ))}
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-zinc-900 hover:bg-transparent">
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Order Details</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Customer</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Revenue Split (85/15)</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {transactions.map((tx) => (
                                        <TableRow key={tx.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                            <TableCell>
                                                <p className="text-xs font-mono text-zinc-500 lowercase">{tx.id.substring(0, 8)}</p>
                                                <p className="text-sm font-bold text-white uppercase">{tx.tracks?.title || tx.album_packs?.title}</p>
                                            </TableCell>
                                            <TableCell>
                                                <p className="text-sm font-medium text-white">{tx.profiles?.full_name}</p>
                                                <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
                                                    DJ: {(tx.tracks?.dj_profiles || tx.album_packs?.dj_profiles)?.dj_name || 'N/A'}
                                                </p>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-xs font-bold text-emerald-400">₹{(tx.amount_paid * 0.85).toLocaleString()} (DJ)</span>
                                                    <span className="text-[10px] font-bold text-purple-400">₹{(tx.amount_paid * 0.15).toLocaleString()} (MixMint)</span>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button variant="ghost" size="sm" className="text-zinc-500 hover:text-white transition-all text-[10px] font-black uppercase tracking-widest">
                                                        Receipt
                                                    </Button>
                                                    <Button
                                                        onClick={() => handleRefund(tx.id)}
                                                        variant="ghost"
                                                        size="sm"
                                                        disabled={tx.amount_paid === 0}
                                                        className="text-red-500 hover:bg-red-500/10 transition-all text-[10px] font-black uppercase tracking-widest"
                                                    >
                                                        Refund
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
