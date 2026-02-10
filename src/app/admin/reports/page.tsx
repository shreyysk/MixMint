'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { AlertTriangle, ExternalLink, CheckCircle, XCircle, Trash2, Eye } from 'lucide-react';
import RequireRole from "@/components/features/auth/RequireRole";

interface CopyrightReport {
    id: string;
    reason: string;
    evidence_url: string | null;
    status: 'pending' | 'reviewed' | 'actioned' | 'rejected';
    created_at: string;
    reporter_id: string;
    profiles: {
        full_name: string;
    };
    tracks: {
        id: string;
        title: string;
    } | null;
    album_packs: {
        id: string;
        title: string;
    } | null;
}

export default function ReportsManagementPage() {
    const [reports, setReports] = useState<CopyrightReport[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadReports();
    }, []);

    async function loadReports() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('copyright_reports')
                .select(`
                    *,
                    profiles (full_name),
                    tracks (id, title),
                    album_packs (id, title)
                `)
                .order('created_at', { ascending: false });

            if (error) throw error;
            setReports(data || []);
        } catch (err) {
            console.error('[LOAD_REPORTS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleStatusChange(reportId: string, newStatus: string) {
        try {
            const { error } = await supabase
                .from('copyright_reports')
                .update({ status: newStatus })
                .eq('id', reportId);

            if (error) throw error;
            setReports(prev => prev.map(r => r.id === reportId ? { ...r, status: newStatus as any } : r));
        } catch (err) {
            console.error('[STATUS_UPDATE_ERROR]', err);
        }
    }

    async function handleTakedown(report: CopyrightReport) {
        try {
            const table = report.tracks ? 'tracks' : 'album_packs';
            const entityId = report.tracks?.id || report.album_packs?.id;

            // In a real prod environment, we might "hide" or move to a "quarantine" bucket
            // For now, let's "hide" by updating a status if it exists, or delete if not.
            // Let's check tracks table for status.

            const { error: deleteError } = await supabase
                .from(table)
                .delete()
                .eq('id', entityId);

            if (deleteError) throw deleteError;

            await handleStatusChange(report.id, 'actioned');
        } catch (err) {
            console.error('[TAKEDOWN_ERROR]', err);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex items-center gap-4 mb-2">
                    <div className="p-3 bg-red-500/10 rounded-2xl border border-red-500/20 shadow-red-glow">
                        <AlertTriangle className="w-8 h-8 text-red-400" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-heading font-bold text-white">Copyright & DMCA</h1>
                        <p className="text-zinc-400">Review and action copyright infringement reports.</p>
                    </div>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-white">Active Reports</CardTitle>
                        <CardDescription>
                            {reports.length} reports total.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <div key={i} className="h-16 bg-zinc-900 rounded-xl" />
                                ))}
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Reporter</TableHead>
                                        <TableHead>Target Content</TableHead>
                                        <TableHead className="w-[300px]">Reason</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {reports.map((report) => (
                                        <TableRow key={report.id}>
                                            <TableCell className="font-medium text-white">
                                                {report.profiles?.full_name}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span className="text-white font-medium">
                                                        {report.tracks?.title || report.album_packs?.title}
                                                    </span>
                                                    <span className="text-[10px] text-zinc-600 font-black uppercase tracking-widest">
                                                        {report.tracks ? 'Track' : 'Album'}
                                                    </span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <p className="text-xs text-zinc-400 line-clamp-2">{report.reason}</p>
                                                {report.evidence_url && (
                                                    <a
                                                        href={report.evidence_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-[10px] text-blue-400 hover:underline flex items-center gap-1 mt-1"
                                                    >
                                                        <ExternalLink className="w-2.5 h-2.5" /> View Evidence
                                                    </a>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <select
                                                    value={report.status}
                                                    onChange={(e) => handleStatusChange(report.id, e.target.value)}
                                                    className="bg-zinc-900 border border-zinc-800 rounded-lg px-2 py-1 text-[10px] font-black uppercase tracking-widest text-zinc-300 focus:outline-none"
                                                >
                                                    <option value="pending">Pending</option>
                                                    <option value="reviewed">Reviewed</option>
                                                    <option value="actioned">Actioned</option>
                                                    <option value="rejected">Rejected</option>
                                                </select>
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleTakedown(report)}
                                                    disabled={report.status === 'actioned'}
                                                    className="bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-600/20 rounded-lg text-xs"
                                                >
                                                    Takedown
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="text-zinc-500 hover:text-white"
                                                >
                                                    <Eye className="w-4 h-4" />
                                                </Button>
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
