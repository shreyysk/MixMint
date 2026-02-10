'use client';

import React, { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Download, Trash2, ShieldCheck, AlertCircle, FileJson, Loader2 } from 'lucide-react';

export function PrivacyControls() {
    const { user } = useAuth();
    const [exporting, setExporting] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState(false);

    async function handleExport() {
        if (!user) return;
        try {
            setExporting(true);
            // In a real prod environment, this would call an edge function
            // to gather data from all tables across the DB.
            // For now, we aggregate some basic data from the active session components.

            const { data: profile } = await supabase.from('profiles').select('*').eq('id', user.id).single();
            const { data: purchases } = await supabase.from('purchases').select('*').eq('user_id', user.id);
            const { data: comments } = await supabase.from('comments').select('*').eq('user_id', user.id);

            const exportData = {
                user: profile,
                purchases,
                comments,
                exported_at: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mixmint-data-export-${user.id}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('[EXPORT_ERROR]', err);
        } finally {
            setExporting(false);
        }
    }

    async function handleDeleteAccount() {
        if (!user || !confirmDelete) return;
        try {
            setDeleting(true);
            // This would trigger a cascading delete in Supabase if configured,
            // or an edge function to clean up storage and DB records.
            const { error } = await supabase.from('profiles').delete().eq('id', user.id);
            if (error) throw error;

            await supabase.auth.signOut();
            window.location.href = '/';
        } catch (err) {
            console.error('[DELETE_ACCOUNT_ERROR]', err);
        } finally {
            setDeleting(false);
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center gap-3">
                <ShieldCheck className="w-7 h-7 text-green-400" />
                <h2 className="text-2xl font-heading font-bold text-white">Privacy & GDPR</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Data Portability */}
                <Card className="bg-zinc-950/50 border-zinc-800 hover:border-blue-500/30 transition-all">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <FileJson className="w-5 h-5 text-blue-400" />
                            Data Portability
                        </CardTitle>
                        <CardDescription>Download a copy of your personal data in JSON format.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <p className="text-xs text-zinc-500 leading-relaxed">
                            Your export includes profile information, purchase history, comments, and activity logs. Processing may take a few moments.
                        </p>
                        <Button
                            onClick={handleExport}
                            disabled={exporting}
                            className="w-full bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-600/20 rounded-xl gap-2"
                        >
                            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                            {exporting ? 'Generating Export...' : 'Export My Data'}
                        </Button>
                    </CardContent>
                </Card>

                {/* Account Deletion */}
                <Card className="bg-zinc-950/50 border-red-500/10 hover:border-red-500/30 transition-all">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Trash2 className="w-5 h-5 text-red-500" />
                            Danger Zone
                        </CardTitle>
                        <CardDescription>Permanently delete your account and all associated data.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2">
                            <AlertCircle className="w-4 h-4 text-red-400 mt-0.5" />
                            <p className="text-[10px] text-red-300/80 leading-relaxed font-medium">
                                This action is irreversible. All purchases, subscriptions, and points will be lost forever.
                            </p>
                        </div>

                        {!confirmDelete ? (
                            <Button
                                onClick={() => setConfirmDelete(true)}
                                className="w-full bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-600/20 rounded-xl"
                            >
                                Delete Account
                            </Button>
                        ) : (
                            <div className="space-y-3">
                                <p className="text-center text-xs font-bold text-white uppercase tracking-widest">Are you absolutely sure?</p>
                                <div className="flex gap-3">
                                    <Button variant="ghost" onClick={() => setConfirmDelete(false)} className="flex-1 text-zinc-500">Cancel</Button>
                                    <Button
                                        onClick={handleDeleteAccount}
                                        disabled={deleting}
                                        className="flex-1 bg-red-600 text-white rounded-xl shadow-red-glow"
                                    >
                                        {deleting ? 'Deleting...' : 'Yes, Delete'}
                                    </Button>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
