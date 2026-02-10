'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { MessageSquare, Send, Reply, MoreVertical, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Comment {
    id: string;
    user_id: string;
    content: string;
    created_at: string;
    profiles: {
        full_name: string;
        avatar_url: string;
    };
    replies?: Comment[];
}

interface CommentSectionProps {
    trackId?: string;
    albumId?: string;
}

export function CommentSection({ trackId, albumId }: CommentSectionProps) {
    const { user } = useAuth();
    const [comments, setComments] = useState<Comment[]>([]);
    const [newComment, setNewComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadComments();
    }, [trackId, albumId]);

    async function loadComments() {
        try {
            let query = supabase
                .from('comments')
                .select(`
                    *,
                    profiles (full_name, avatar_url)
                `)
                .is('parent_id', null) // Only top-level comments
                .order('created_at', { ascending: false });

            if (trackId) query = query.eq('track_id', trackId);
            if (albumId) query = query.eq('album_id', albumId);

            const { data, error } = await query;
            if (error) throw error;
            setComments(data || []);
        } catch (err) {
            console.error('[LOAD_COMMENTS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!user || !newComment.trim() || submitting) return;

        try {
            setSubmitting(true);
            const { error } = await supabase.from('comments').insert({
                user_id: user.id,
                track_id: trackId,
                album_id: albumId,
                content: newComment.trim()
            });

            if (error) throw error;
            setNewComment('');
            loadComments();
        } catch (err) {
            console.error('[POST_COMMENT_ERROR]', err);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center gap-3">
                <MessageSquare className="w-6 h-6 text-purple-400" />
                <h3 className="text-xl font-heading font-bold text-white">Discussion</h3>
                <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                    {comments.length} Comments
                </span>
            </div>

            {/* Comment Input */}
            {user ? (
                <form onSubmit={handleSubmit} className="flex gap-4">
                    <Avatar src={user.user_metadata?.avatar_url} fallback={user.user_metadata?.full_name?.[0] || 'U'} className="w-10 h-10 border border-zinc-800" />
                    <div className="flex-1 relative group">
                        <textarea
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            placeholder="Write a comment..."
                            className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-all resize-none h-24"
                        />
                        <div className="absolute bottom-3 right-3">
                            <Button
                                type="submit"
                                size="sm"
                                disabled={!newComment.trim() || submitting}
                                className="bg-purple-600 hover:bg-purple-500 text-white gap-2 rounded-xl shadow-purple-glow"
                            >
                                <Send className="w-4 h-4" />
                                Post
                            </Button>
                        </div>
                    </div>
                </form>
            ) : (
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 text-center">
                    <p className="text-zinc-400 text-sm mb-4">Sign in to join the conversation.</p>
                    <Button variant="outline" className="rounded-xl border-zinc-700">Explore Login Options</Button>
                </div>
            )}

            {/* Comments List */}
            <div className="space-y-6">
                {loading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex gap-4 animate-pulse">
                            <div className="w-10 h-10 bg-zinc-800 rounded-full" />
                            <div className="flex-1 space-y-2">
                                <div className="h-4 bg-zinc-800 rounded w-1/4" />
                                <div className="h-16 bg-zinc-800 rounded w-full" />
                            </div>
                        </div>
                    ))
                ) : comments.length > 0 ? (
                    comments.map((comment) => (
                        <div key={comment.id} className="flex gap-4 group">
                            <Avatar src={comment.profiles?.avatar_url} fallback={comment.profiles?.full_name?.[0] || '?'} className="w-10 h-10 border border-zinc-800" />
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-white">{comment.profiles?.full_name}</span>
                                        <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest">
                                            {new Date(comment.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <button className="text-zinc-600 hover:text-white transition-colors">
                                        <MoreVertical className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-2xl p-4 group-hover:bg-zinc-900/50 transition-colors">
                                    <p className="text-zinc-300 text-sm leading-relaxed">{comment.content}</p>
                                </div>
                                <div className="flex items-center gap-4 text-xs font-bold text-zinc-500 uppercase tracking-widest">
                                    <button className="flex items-center gap-2 hover:text-purple-400 transition-colors">
                                        <Reply className="w-3 h-3" />
                                        Reply
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-center py-12">
                        <MessageSquare className="w-10 h-10 text-zinc-800 mx-auto mb-4" />
                        <p className="text-zinc-500 text-sm">No comments yet. Be the first to start the discussion!</p>
                    </div>
                )}
            </div>
        </div>
    );
}
