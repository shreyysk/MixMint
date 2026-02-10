'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import {
    Music,
    Star,
    TrendingUp,
    ShieldAlert,
    MoreVertical,
    Search,
    Download,
    Mail,
    Settings,
    UserMinus
} from 'lucide-react';
import { ExportButton } from '@/components/ui/ExportButton';

interface DJProfile {
    id: string;
    dj_name: string;
    slug: string;
    status: string;
    profiles: {
        email: string;
        full_name: string;
        avatar_url: string;
    };
    tracks_count: number;
    sub_count: number;
}

export default function DJManagementPage() {
    const [djs, setDjs] = useState<DJProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadDJs();
    }, []);

    async function loadDJs() {
        try {
            setLoading(true);

            // In a real prod setup, these counts would come from a view or aggregation
            const { data, error } = await supabase
                .from('dj_profiles')
                .select(`
                    *,
                    profiles (email, full_name, avatar_url)
                `)
                .neq('status', 'pending');

            if (error) throw error;

            // Mocking some counts for display
            const djsWithStats = (data || []).map(dj => ({
                ...dj,
                tracks_count: Math.floor(Math.random() * 50),
                sub_count: Math.floor(Math.random() * 200)
            }));

            setDjs(djsWithStats);
        } catch (err) {
            console.error('[LOAD_DJS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    const filteredDjs = djs.filter(dj =>
        dj.dj_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        dj.profiles?.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-blue-glow">
                            <Music className="w-8 h-8 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">DJ Management</h1>
                            <p className="text-zinc-400">Oversee active DJs, performance, and account status.</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <ExportButton
                            data={djs.map(dj => ({
                                name: dj.dj_name,
                                email: dj.profiles?.email,
                                tracks: dj.tracks_count,
                                subscribers: dj.sub_count,
                                status: dj.status
                            }))}
                            filename="mixmint_djs"
                        />
                        <div className="relative group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-blue-400 transition-colors" size={18} />
                            <input
                                type="text"
                                placeholder="Search DJs..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="bg-zinc-900 border border-zinc-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-all w-full md:w-64"
                            />
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-purple-500/10 rounded-xl">
                                <TrendingUp className="w-6 h-6 text-purple-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Total DJ Revenue</p>
                                <p className="text-2xl font-bold text-white">₹4,25,000</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-xl">
                                <Star className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Global Subscribers</p>
                                <p className="text-2xl font-bold text-white">1,240</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-pink-500/10 rounded-xl">
                                <Music className="w-6 h-6 text-pink-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Active Tracks</p>
                                <p className="text-2xl font-bold text-white">8,420</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader>
                        <CardTitle className="text-white">Active DJs</CardTitle>
                        <CardDescription>Comprehensive list of DJs currently on the platform.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 10 }).map((_, i) => (
                                    <div key={i} className="h-16 bg-zinc-900 rounded-xl" />
                                ))}
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-zinc-900 hover:bg-transparent">
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">DJ Profile</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Status</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Tracks</TableHead>
                                        <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest text-center">Subs</TableHead>
                                        <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredDjs.map((dj) => (
                                        <TableRow key={dj.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Avatar
                                                        src={dj.profiles?.avatar_url}
                                                        fallback={dj.dj_name[0]}
                                                        className="w-10 h-10 border border-zinc-800"
                                                    />
                                                    <div>
                                                        <p className="font-bold text-white group-hover:text-blue-400 transition-colors uppercase tracking-tight">{dj.dj_name}</p>
                                                        <p className="text-[10px] text-zinc-500 font-bold lowercase">{dj.profiles?.email}</p>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className={`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider w-fit border ${dj.status === 'approved'
                                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                                                    }`}>
                                                    {dj.status}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <span className="text-xs font-bold text-zinc-300">{dj.tracks_count}</span>
                                            </TableCell>
                                            <TableCell className="text-center">
                                                <span className="text-xs font-bold text-zinc-300">{dj.sub_count}</span>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex items-center justify-end gap-1">
                                                    <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-lg">
                                                        <Mail size={16} />
                                                    </Button>
                                                    <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-lg">
                                                        <TrendingUp size={16} />
                                                    </Button>
                                                    <Button size="sm" variant="ghost" className="text-red-500/50 hover:text-red-500 rounded-lg">
                                                        <UserMinus size={16} />
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
