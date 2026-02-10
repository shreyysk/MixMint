'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    Megaphone,
    Flag,
    Plus,
    Trash2,
    Save,
    Globe,
    Users,
    Music,
    ToggleLeft as Toggle,
    RefreshCw,
    Activity,
    Wifi,
    Cpu,
    HardDrive,
    Server
} from 'lucide-react';

interface Announcement {
    id: string;
    title: string;
    content: string;
    target_audience: string;
    active: boolean;
    created_at: string;
}

interface FeatureFlag {
    id: string;
    name: string;
    description: string;
    is_enabled: boolean;
}

export default function OperationsPage() {
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [flags, setFlags] = useState<FeatureFlag[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            setLoading(true);
            const [annRes, flagRes] = await Promise.all([
                supabase.from('announcements').select('*').order('created_at', { ascending: false }),
                supabase.from('feature_flags').select('*').order('name', { ascending: true })
            ]);

            setAnnouncements(annRes.data || []);
            setFlags(flagRes.data || []);
        } catch (err) {
            console.error('[LOAD_OPS_DATA_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function toggleFlag(id: string, current: boolean) {
        try {
            const { error } = await supabase
                .from('feature_flags')
                .update({ is_enabled: !current })
                .eq('id', id);

            if (error) throw error;
            setFlags(prev => prev.map(f => f.id === id ? { ...f, is_enabled: !current } : f));
        } catch (err) {
            console.error('[TOGGLE_FLAG_ERROR]', err);
        }
    }

    async function deleteAnnouncement(id: string) {
        if (!confirm('Are you sure?')) return;
        try {
            const { error } = await supabase.from('announcements').delete().eq('id', id);
            if (error) throw error;
            setAnnouncements(prev => prev.filter(a => a.id !== id));
        } catch (err) {
            console.error('[DELETE_ANN_ERROR]', err);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-zinc-800 rounded-2xl border border-zinc-700">
                            <Activity className="w-8 h-8 text-zinc-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Platform Operations</h1>
                            <p className="text-zinc-400">Manage global announcements and internal system feature flags.</p>
                        </div>
                    </div>
                </div>

                {/* System Health */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 bg-zinc-950/20 border border-emerald-500/10 rounded-2xl flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg">
                            <Wifi className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1">API Status</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tight">Healthy</p>
                        </div>
                    </div>
                    <div className="p-4 bg-zinc-950/20 border border-emerald-500/10 rounded-2xl flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg">
                            <Cpu className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1">CPU Load</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tight">12%</p>
                        </div>
                    </div>
                    <div className="p-4 bg-zinc-950/20 border border-emerald-500/10 rounded-2xl flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg">
                            <HardDrive className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1">DB Storage</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tight">8.4 GB / 20</p>
                        </div>
                    </div>
                    <div className="p-4 bg-zinc-950/20 border border-emerald-500/10 rounded-2xl flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg">
                            <Server className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1">Uptime</p>
                            <p className="text-xs font-bold text-white uppercase tracking-tight">99.98%</p>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Announcements Section */}
                    <Card className="bg-zinc-950/50 border-zinc-900">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle className="text-white flex items-center gap-2">
                                    <Megaphone className="w-5 h-5 text-orange-400" />
                                    Announcements
                                </CardTitle>
                                <CardDescription>Post news for users and DJs.</CardDescription>
                            </div>
                            <Button size="sm" className="bg-orange-500/10 hover:bg-orange-500/20 text-orange-500 border border-orange-500/20 rounded-xl gap-2">
                                <Plus size={14} />
                                New
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {announcements.map((ann) => (
                                    <div key={ann.id} className="p-4 bg-zinc-900/40 rounded-2xl border border-zinc-900 group hover:border-zinc-700 transition-all">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="font-bold text-white uppercase tracking-tight text-sm">{ann.title}</h4>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2 py-0.5 rounded-full text-[8px] font-black uppercase tracking-widest ${ann.target_audience === 'all' ? 'bg-blue-500/10 text-blue-400' :
                                                    ann.target_audience === 'djs' ? 'bg-purple-500/10 text-purple-400' :
                                                        'bg-emerald-500/10 text-emerald-400'
                                                    }`}>
                                                    {ann.target_audience}
                                                </span>
                                                <button
                                                    onClick={() => deleteAnnouncement(ann.id)}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-600 hover:text-red-500"
                                                >
                                                    <Trash2 size={12} />
                                                </button>
                                            </div>
                                        </div>
                                        <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{ann.content}</p>
                                        <div className="text-[9px] text-zinc-600 font-bold uppercase tracking-widest">
                                            Posted: {new Date(ann.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                ))}
                                {announcements.length === 0 && (
                                    <div className="text-center py-12 text-zinc-600 italic text-xs">No active announcements.</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Feature Flags Section */}
                    <Card className="bg-zinc-950/50 border-zinc-900 text-white">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <Flag className="w-5 h-5 text-blue-400" />
                                Feature Flags
                            </CardTitle>
                            <CardDescription>Safely toggle experimental features.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {flags.map((flag) => (
                                    <div key={flag.id} className="flex items-center justify-between p-4 bg-zinc-900/40 rounded-2xl border border-zinc-900">
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2">
                                                <h4 className="font-mono text-sm text-zinc-300">{flag.name}</h4>
                                                {flag.is_enabled && (
                                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-emerald-glow" />
                                                )}
                                            </div>
                                            <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest leading-relaxed">
                                                {flag.description}
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => toggleFlag(flag.id, flag.is_enabled)}
                                            className={`w-10 h-5 rounded-full transition-all relative ${flag.is_enabled ? 'bg-emerald-600 shadow-emerald-glow' : 'bg-zinc-800'}`}
                                        >
                                            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${flag.is_enabled ? 'left-5.5' : 'left-0.5'}`} />
                                        </button>
                                    </div>
                                ))}
                                {flags.length === 0 && (
                                    <div className="text-center py-12 text-zinc-600 italic text-xs">No feature flags registered.</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </RequireRole>
    );
}
