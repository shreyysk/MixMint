'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import {
    UserCheck,
    UserX,
    ExternalLink,
    Clock,
    CheckCircle2,
    XCircle,
    Search,
    Filter
} from 'lucide-react';

interface DJApplication {
    id: string;
    dj_name: string;
    bio: string;
    slug: string;
    status: 'pending' | 'approved' | 'rejected' | 'banned';
    created_at: string;
    profiles: {
        full_name: string;
        avatar_url: string;
    };
}

export default function DJApprovalsPage() {
    const [applications, setApplications] = useState<DJApplication[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadApplications();
    }, []);

    async function loadApplications() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('dj_profiles')
                .select(`
                    *,
                    profiles (full_name, avatar_url)
                `)
                .eq('status', 'pending')
                .order('created_at', { ascending: false });

            if (error) throw error;
            setApplications(data || []);
        } catch (err) {
            console.error('[LOAD_DJ_APPS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleAction(id: string, newStatus: 'approved' | 'rejected') {
        try {
            const { error } = await supabase
                .from('dj_profiles')
                .update({ status: newStatus })
                .eq('id', id);

            if (error) throw error;

            // If approved, we might want to also update the user's role to 'dj' in the profiles table
            if (newStatus === 'approved') {
                await supabase.from('profiles').update({ role: 'dj' }).eq('id', id);
            }

            setApplications(prev => prev.filter(app => app.id !== id));
        } catch (err) {
            console.error('[DJ_ACTION_ERROR]', err);
        }
    }

    const filteredApps = applications.filter(app =>
        app.dj_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.profiles?.full_name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-purple-glow">
                            <UserCheck className="w-8 h-8 text-purple-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">DJ Applications</h1>
                            <p className="text-zinc-400">Review and approve new DJ registrations.</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <div className="relative group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-purple-400 transition-colors" size={18} />
                            <input
                                type="text"
                                placeholder="Search applications..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="bg-zinc-900 border border-zinc-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-all w-full md:w-64"
                            />
                        </div>
                    </div>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Clock className="w-5 h-5 text-blue-400" />
                            Pending Review
                        </CardTitle>
                        <CardDescription>
                            {applications.length} DJs waiting for platform access.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <div key={i} className="h-20 bg-zinc-900 rounded-2xl" />
                                ))}
                            </div>
                        ) : filteredApps.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-zinc-900 hover:bg-transparent">
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">DJ Info</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Bio Snippet</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Applied Date</TableHead>
                                        <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredApps.map((app) => (
                                        <TableRow key={app.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Avatar
                                                        src={app.profiles?.avatar_url}
                                                        fallback={app.dj_name[0]}
                                                        className="w-10 h-10 border border-zinc-800 group-hover:border-purple-500/50 transition-colors"
                                                    />
                                                    <div>
                                                        <p className="font-bold text-white">{app.dj_name}</p>
                                                        <p className="text-xs text-zinc-500">{app.profiles?.full_name}</p>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <p className="text-sm text-zinc-400 line-clamp-1 max-w-xs">{app.bio}</p>
                                            </TableCell>
                                            <TableCell>
                                                <span className="text-xs text-zinc-500 font-medium">
                                                    {new Date(app.created_at).toLocaleDateString()}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleAction(app.id, 'approved')}
                                                        className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg gap-2"
                                                    >
                                                        <CheckCircle2 size={14} />
                                                        Approve
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleAction(app.id, 'rejected')}
                                                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg gap-2"
                                                    >
                                                        <XCircle size={14} />
                                                        Reject
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-20 border border-dashed border-zinc-900 rounded-3xl bg-zinc-900/10">
                                <UserX className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                                <h3 className="text-lg font-bold text-zinc-500">No Pending Applications</h3>
                                <p className="text-zinc-600 text-sm max-w-xs mx-auto">All DJ applications have been processed. Great job!</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
