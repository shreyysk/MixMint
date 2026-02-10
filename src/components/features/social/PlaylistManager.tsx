'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/lib/AuthContext';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Music, Users, Lock, Globe, Trash2, Edit2 } from 'lucide-react';

interface Playlist {
    id: string;
    title: string;
    description: string | null;
    is_public: boolean;
    is_collaborative: boolean;
    user_id: string;
    created_at: string;
    _count?: {
        playlist_tracks: number;
    };
}

export function PlaylistManager() {
    const { user } = useAuth();
    const [playlists, setPlaylists] = useState<Playlist[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [newTitle, setNewTitle] = useState('');

    useEffect(() => {
        if (user) loadPlaylists();
    }, [user]);

    async function loadPlaylists() {
        try {
            const { data, error } = await supabase
                .from('playlists')
                .select(`
                    *,
                    playlist_tracks (count)
                `)
                .eq('user_id', user?.id)
                .order('created_at', { ascending: false });

            if (error) throw error;
            setPlaylists(data || []);
        } catch (err) {
            console.error('[LOAD_PLAYLISTS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate(e: React.FormEvent) {
        e.preventDefault();
        if (!user || !newTitle.trim()) return;

        try {
            const { error } = await supabase.from('playlists').insert({
                user_id: user.id,
                title: newTitle.trim(),
                is_public: true,
                is_collaborative: false
            });

            if (error) throw error;
            setNewTitle('');
            setShowCreate(false);
            loadPlaylists();
        } catch (err) {
            console.error('[CREATE_PLAYLIST_ERROR]', err);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-heading font-bold text-white">Your Playlists</h2>
                    <p className="text-zinc-500 text-sm">Create and manage your music collections.</p>
                </div>
                <Button
                    onClick={() => setShowCreate(true)}
                    className="bg-purple-600 hover:bg-purple-500 text-white gap-2 rounded-xl shadow-purple-glow"
                >
                    <Plus className="w-4 h-4" />
                    New Playlist
                </Button>
            </div>

            {showCreate && (
                <Card className="bg-zinc-900/50 border-purple-500/30 animate-in slide-in-from-top duration-300">
                    <CardContent className="pt-6">
                        <form onSubmit={handleCreate} className="space-y-4">
                            <div>
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1 block">Playlist Name</label>
                                <input
                                    type="text"
                                    value={newTitle}
                                    onChange={(e) => setNewTitle(e.target.value)}
                                    placeholder="Enter playlist title..."
                                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500 transition-all"
                                    autoFocus
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}>Cancel</Button>
                                <Button size="sm" type="submit" disabled={!newTitle.trim()} className="bg-purple-600 text-white">Create</Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="h-48 bg-zinc-900 animate-pulse rounded-2xl" />
                    ))
                ) : playlists.length > 0 ? (
                    playlists.map((playlist) => (
                        <Card key={playlist.id} className="bg-zinc-950 border-zinc-800 hover:border-purple-500/50 transition-all group overflow-hidden">
                            <CardContent className="p-0">
                                <div className="aspect-video bg-gradient-to-br from-purple-900/40 to-black relative flex items-center justify-center">
                                    <Music className="w-12 h-12 text-purple-500/30" />
                                    <div className="absolute top-3 right-3 flex gap-2">
                                        {playlist.is_collaborative && (
                                            <div className="bg-blue-500/20 border border-blue-500/30 p-1.5 rounded-lg backdrop-blur-md">
                                                <Users className="w-4 h-4 text-blue-400" />
                                            </div>
                                        )}
                                        {playlist.is_public ? (
                                            <div className="bg-zinc-800/50 border border-white/5 p-1.5 rounded-lg backdrop-blur-md">
                                                <Globe className="w-4 h-4 text-zinc-400" />
                                            </div>
                                        ) : (
                                            <div className="bg-zinc-800/50 border border-white/5 p-1.5 rounded-lg backdrop-blur-md">
                                                <Lock className="w-4 h-4 text-zinc-400" />
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="p-5 space-y-3">
                                    <div>
                                        <h3 className="font-bold text-white group-hover:text-purple-400 transition-colors truncate">{playlist.title}</h3>
                                        <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mt-1">
                                            {playlist.is_collaborative ? 'Collaborative' : 'Private'} • Track count: 0
                                        </p>
                                    </div>
                                    <div className="flex items-center justify-between pt-2 border-t border-zinc-900">
                                        <div className="flex gap-2">
                                            <button className="p-2 hover:bg-zinc-900 rounded-lg text-zinc-500 hover:text-white transition-all">
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button className="p-2 hover:bg-zinc-900 rounded-lg text-zinc-500 hover:text-red-400 transition-all">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                        <Button variant="ghost" size="sm" className="text-purple-400 text-xs font-bold uppercase tracking-wider">
                                            View Details
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))
                ) : (
                    <div className="col-span-full py-20 bg-zinc-900/30 border border-dashed border-zinc-800 rounded-3xl text-center">
                        <Music className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                        <h3 className="text-lg font-bold text-zinc-400">No Playlist Found</h3>
                        <p className="text-zinc-600 text-sm max-w-xs mx-auto mb-6">Start building your collection by creating your first playlist.</p>
                        <Button onClick={() => setShowCreate(true)} className="bg-zinc-800 text-zinc-300">Create Playlist</Button>
                    </div>
                )}
            </div>
        </div>
    );
}
