'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    Monitor,
    Smartphone,
    Globe,
    History,
    ShieldAlert,
    RefreshCw,
    Search,
    MapPin
} from 'lucide-react';

interface SecurityEvent {
    id: string;
    event_type: string;
    user_id: string;
    profiles: {
        email: string;
        full_name: string;
    };
    ip_address: string;
    user_agent: string;
    metadata: any;
    created_at: string;
}

export default function SecurityAuditPage() {
    const [events, setEvents] = useState<SecurityEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadSecurityEvents();
    }, []);

    async function loadSecurityEvents() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('suspicious_activity')
                .select(`
                    *,
                    profiles (email, full_name)
                `)
                .order('created_at', { ascending: false })
                .limit(50);

            if (error) throw error;
            setEvents(data || []);
        } catch (err) {
            console.error('[LOAD_SECURITY_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-red-500/10 rounded-2xl border border-red-500/20 shadow-red-glow">
                            <ShieldAlert className="w-8 h-8 text-red-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Security Audit & Intelligence</h1>
                            <p className="text-zinc-400">Monitor device access, suspicious activity, and platform integrity.</p>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-xl">
                                <Globe className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Active IPs</p>
                                <p className="text-2xl font-bold text-white">1,240</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-orange-500/10 rounded-xl">
                                <ShieldAlert className="w-6 h-6 text-orange-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Flagged Devices</p>
                                <p className="text-2xl font-bold text-white">12</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-zinc-900">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-red-500/10 rounded-xl">
                                <History className="w-6 h-6 text-red-500" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Recent Blocks</p>
                                <p className="text-2xl font-bold text-white">4</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-900">
                        <div>
                            <CardTitle className="text-white flex items-center gap-2">
                                <History className="w-5 h-5 text-red-400" />
                                Security Event Stream
                            </CardTitle>
                            <CardDescription>Real-time audit of authentication and high-risk events.</CardDescription>
                        </div>
                        <Button variant="ghost" size="sm" onClick={loadSecurityEvents} className="text-zinc-500 hover:text-white">
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="border-zinc-900 hover:bg-transparent px-4">
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest pl-6">Event Type</TableHead>
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Identity</TableHead>
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Technical Data (IP/UA)</TableHead>
                                    <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest pr-6">Timestamp</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {events.map((event) => (
                                    <TableRow key={event.id} className="border-zinc-900 hover:bg-red-500/5 transition-colors group">
                                        <TableCell className="pl-6">
                                            <div className="flex items-center gap-3">
                                                <div className={`p-1.5 rounded-lg ${event.event_type.includes('fail') ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
                                                    <ShieldAlert size={14} />
                                                </div>
                                                <p className="text-xs font-black uppercase tracking-wider text-white">{event.event_type.replace(/_/g, ' ')}</p>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <p className="text-sm font-medium text-white">{event.profiles?.full_name || 'Anonymous'}</p>
                                            <p className="text-[10px] text-zinc-600 font-bold lowercase">{event.profiles?.email || 'unknown@mixmint.site'}</p>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-1.5 text-zinc-400">
                                                    <MapPin size={10} className="text-zinc-600" />
                                                    <span className="text-[10px] font-mono">{event.ip_address || '0.0.0.0'}</span>
                                                </div>
                                                <div className="flex items-center gap-1.5 text-zinc-500">
                                                    {event.user_agent?.toLowerCase().includes('mobile') ? <Smartphone size={10} /> : <Monitor size={10} />}
                                                    <span className="text-[10px] truncate max-w-[200px] font-mono">{event.user_agent || 'Unknown UA'}</span>
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right pr-6">
                                            <p className="text-[10px] text-zinc-500 font-bold">{new Date(event.created_at).toLocaleString()}</p>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {events.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={4} className="h-48 text-center">
                                            <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest">No security events recorded (Safe State)</p>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
