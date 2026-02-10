'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { MessageSquare, CheckCircle, XCircle, ShieldAlert, Flag } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import RequireRole from "@/components/features/auth/RequireRole";

interface Comment {
    id: string;
    content: string;
    is_moderated: boolean;
    created_at: string;
    user_id: string;
    profiles: {
        full_name: string;
        avatar_url: string;
    };
    tracks: {
        title: string;
    } | null;
    album_packs: {
        title: string;
    } | null;
}

export default function ModerationPage() {
    const [comments, setComments] = useState<Comment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadPendingComments();
    }, []);

    async function loadPendingComments() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('comments')
                .select(`
                    *,
                    profiles (full_name, avatar_url),
                    tracks (title),
                    album_packs (title)
                `)
                .eq('is_moderated', false)
                .order('created_at', { ascending: false });

            if (error) throw error;
            setComments(data || []);
        } catch (err) {
            console.error('[LOAD_MODERATION_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleApprove(id: string) {
        try {
            const { error } = await supabase
                .from('comments')
                .update({ is_moderated: true })
                .eq('id', id);

            if (error) throw error;
            setComments(prev => prev.filter(c => c.id !== id));
        } catch (err) {
            console.error('[APPROVE_ERROR]', err);
        }
    }

    async function handleDelete(id: string) {
        try {
            const { error } = await supabase
                .from('comments')
                .delete()
                .eq('id', id);

            if (error) throw error;
            setComments(prev => prev.filter(c => c.id !== id));
        } catch (err) {
            console.error('[DELETE_ERROR]', err);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex items-center gap-4 mb-2">
                    <div className="p-3 bg-orange-500/10 rounded-2xl border border-orange-500/20 shadow-orange-glow">
                        <ShieldAlert className="w-8 h-8 text-orange-400" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-heading font-bold text-white">Moderation Queue</h1>
                        <p className="text-zinc-400">Review and moderate community comments.</p>
                    </div>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <MessageSquare className="w-5 h-5 text-purple-400" />
                            Pending Comments
                        </CardTitle>
                        <CardDescription>
                            {comments.length} comments awaiting review.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <div key={i} className="h-16 bg-zinc-900 rounded-xl" />
                                ))}
                            </div>
                        ) : comments.length > 0 ? (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>User</TableHead>
                                        <TableHead>Target</TableHead>
                                        <TableHead className="w-[400px]">Content</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {comments.map((comment) => (
                                        <TableRow key={comment.id}>
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Avatar src={comment.profiles?.avatar_url} fallback={comment.profiles?.full_name?.[0]} className="w-8 h-8" />
                                                    <span className="font-medium text-white">{comment.profiles?.full_name}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <span className="text-xs text-zinc-500 font-bold uppercase tracking-wider">
                                                    {comment.tracks?.title || comment.album_packs?.title || 'Unknown'}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <p className="text-sm text-zinc-300 break-words">{comment.content}</p>
                                            </TableCell>
                                            <TableCell className="text-zinc-500 text-xs">
                                                {new Date(comment.created_at).toLocaleDateString()}
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleApprove(comment.id)}
                                                    className="bg-green-600/10 hover:bg-green-600/20 text-green-400 border border-green-600/20 rounded-lg"
                                                >
                                                    <CheckCircle className="w-4 h-4" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleDelete(comment.id)}
                                                    className="bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-600/20 rounded-lg"
                                                >
                                                    <XCircle className="w-4 h-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <div className="text-center py-20 border border-dashed border-zinc-800 rounded-2xl bg-zinc-900/10">
                                <Flag className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                                <h3 className="text-lg font-bold text-zinc-500">Queue Clear</h3>
                                <p className="text-zinc-600 text-sm">No pending comments to moderate.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
