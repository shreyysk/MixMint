'use client';

import React, { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { AlertCircle, Shield, LucideIcon, Send, CheckCircle2 } from 'lucide-react';

interface CopyrightReportFormProps {
    trackId?: string;
    albumId?: string;
    title: string;
    onClose: () => void;
}

export function CopyrightReportForm({ trackId, albumId, title, onClose }: CopyrightReportFormProps) {
    const { user } = useAuth();
    const [reason, setReason] = useState('');
    const [evidence, setEvidence] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!user || !reason.trim()) return;

        try {
            setLoading(true);
            const { error } = await supabase.from('copyright_reports').insert({
                reporter_id: user.id,
                track_id: trackId,
                album_id: albumId,
                reason: reason.trim(),
                evidence_url: evidence.trim(),
                status: 'pending'
            });

            if (error) throw error;
            setSuccess(true);
        } catch (err) {
            console.error('[REPORT_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    if (success) {
        return (
            <Card className="bg-zinc-950 border-green-500/30 text-center py-10 px-6">
                <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-white mb-2">Report Submitted</h3>
                <p className="text-zinc-400 text-sm mb-6">Our moderation team will review your claim and take appropriate action.</p>
                <Button onClick={onClose} className="bg-green-600 text-white rounded-xl">Close</Button>
            </Card>
        );
    }

    return (
        <Card className="bg-zinc-950 border-zinc-800 shadow-2xl animate-in zoom-in-95 duration-300">
            <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                    <AlertCircle className="w-5 h-5 text-red-400" />
                    <CardTitle className="text-white">Report Copyright Infringement</CardTitle>
                </div>
                <CardDescription>
                    Submit a DMCA takedown notice for "<span className="text-white font-medium">{title}</span>".
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Reason for Takedown</label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Please provide details of the infringement..."
                            required
                            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all h-32 resize-none"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest block">Supporting Evidence (URL)</label>
                        <input
                            type="url"
                            value={evidence}
                            onChange={(e) => setEvidence(e.target.value)}
                            placeholder="Link to original work or proof of ownership"
                            className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all"
                        />
                    </div>

                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3">
                        <Shield className="w-5 h-5 text-red-400 mt-0.5" />
                        <p className="text-[11px] text-red-200/60 leading-relaxed font-medium">
                            Misuse of this form may result in account termination. By submitting this report, you confirm that you have a good faith belief that the use of the material is not authorized.
                        </p>
                    </div>

                    <div className="flex gap-4">
                        <Button variant="ghost" onClick={onClose} className="flex-1 text-zinc-500 rounded-xl">Cancel</Button>
                        <Button
                            type="submit"
                            disabled={loading || !reason.trim()}
                            className="flex-1 bg-red-600 hover:bg-red-500 text-white rounded-xl shadow-red-glow gap-2"
                        >
                            <Send className="w-4 h-4" />
                            {loading ? 'Submitting...' : 'Submit Notice'}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}
