'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    MessageSquare,
    Clock,
    AlertCircle,
    CheckCircle2,
    MoreVertical,
    Filter,
    Search,
    User,
    ArrowUpRight
} from 'lucide-react';

interface SupportTicket {
    id: string;
    subject: string;
    category: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    status: 'open' | 'in_progress' | 'resolved' | 'closed';
    created_at: string;
    description: string;
    profiles: {
        full_name: string;
        email: string;
    };
}

export default function SupportTicketsPage() {
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        loadTickets();
    }, [filter]);

    async function loadTickets() {
        try {
            setLoading(true);
            let query = supabase
                .from('support_tickets')
                .select(`
                    *,
                    profiles (full_name, email)
                `)
                .order('created_at', { ascending: false });

            if (filter !== 'all') {
                query = query.eq('status', filter);
            }

            const { data, error } = await query;
            if (error) throw error;
            setTickets(data || []);
        } catch (err) {
            console.error('[LOAD_TICKETS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function updateStatus(id: string, status: string) {
        try {
            const { error } = await supabase
                .from('support_tickets')
                .update({ status })
                .eq('id', id);

            if (error) throw error;
            setTickets(prev => prev.map(t => t.id === id ? { ...t, status: status as any } : t));
        } catch (err) {
            console.error('[UPDATE_STATUS_ERROR]', err);
        }
    }

    const priorityColor = (p: string) => {
        switch (p) {
            case 'urgent': return 'text-red-500 bg-red-500/10 border-red-500/20';
            case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
            case 'medium': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
            default: return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
        }
    };

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-blue-glow">
                            <MessageSquare className="w-8 h-8 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Support Tickets</h1>
                            <p className="text-zinc-400">Respond to user inquiries and technical issues.</p>
                        </div>
                    </div>

                    <div className="flex bg-zinc-900/50 p-1 rounded-xl border border-zinc-800">
                        {['all', 'open', 'in_progress', 'resolved'].map((f) => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all ${filter === f ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
                            >
                                {f.replace('_', ' ')}
                            </button>
                        ))}
                    </div>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader>
                        <CardTitle className="text-white">Active Ticket Queue</CardTitle>
                        <CardDescription>
                            {tickets.length} tickets found.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <div key={i} className="h-16 bg-zinc-900 rounded-xl" />
                                ))}
                            </div>
                        ) : tickets.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow className="hover:bg-transparent border-zinc-900">
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Priority</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Ticket / Subject</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Reporter</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Status</TableHead>
                                        <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {tickets.map((t) => (
                                        <TableRow key={t.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                            <TableCell>
                                                <div className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest border w-fit ${priorityColor(t.priority)}`}>
                                                    {t.priority}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors uppercase tracking-tight">{t.subject}</span>
                                                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Category: {t.category}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-2">
                                                    <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                                                        <User className="w-4 h-4 text-zinc-600" />
                                                    </div>
                                                    <div>
                                                        <p className="text-xs font-bold text-zinc-300">{t.profiles?.full_name}</p>
                                                        <p className="text-[10px] text-zinc-500 lowercase">{t.profiles?.email}</p>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <select
                                                    value={t.status}
                                                    onChange={(e) => updateStatus(t.id, e.target.value)}
                                                    className="bg-zinc-900 border border-zinc-800 rounded-lg px-2 py-1 text-[10px] font-black uppercase tracking-widest text-zinc-400 focus:outline-none focus:border-blue-500"
                                                >
                                                    <option value="open">Open</option>
                                                    <option value="in_progress">In Progress</option>
                                                    <option value="resolved">Resolved</option>
                                                    <option value="closed">Closed</option>
                                                </select>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-lg">
                                                    <ArrowUpRight size={14} />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-20 bg-zinc-900/10 border border-dashed border-zinc-900 rounded-3xl">
                                <MessageSquare className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                                <h3 className="text-lg font-bold text-zinc-500">Inbox Clear</h3>
                                <p className="text-zinc-600 text-sm">No support tickets match your filter.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
