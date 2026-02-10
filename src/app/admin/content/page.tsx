'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
  Music,
  Layers,
  Play,
  Trash2,
  AlertTriangle,
  Eye,
  Search,
  Download,
  CheckCircle,
  XCircle,
  MoreVertical
} from 'lucide-react';

interface ContentItem {
  id: string;
  title: string;
  type: 'track' | 'album';
  dj_name: string;
  created_at: string;
  price: number;
  status: string;
}

export default function ContentModerationPage() {
  const [content, setContent] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'all' | 'tracks' | 'albums'>('all');

  useEffect(() => {
    loadContent();
  }, [tab]);

  async function loadContent() {
    try {
      setLoading(true);

      let queryDetails = [];

      if (tab === 'all' || tab === 'tracks') {
        const { data: tracks } = await supabase
          .from('tracks')
          .select(`
                        id,
                        title,
                        created_at,
                        price,
                        dj_profiles (dj_name)
                    `)
          .order('created_at', { ascending: false })
          .limit(20);

        if (tracks) {
          queryDetails.push(...tracks.map((t: any) => ({
            ...t,
            type: 'track' as const,
            dj_name: (Array.isArray(t.dj_profiles) ? t.dj_profiles[0]?.dj_name : t.dj_profiles?.dj_name) || 'Unknown',
            status: 'active'
          })));
        }
      }

      if (tab === 'all' || tab === 'albums') {
        const { data: albums } = await supabase
          .from('album_packs')
          .select(`
                        id,
                        title,
                        created_at,
                        price,
                        dj_profiles (dj_name)
                    `)
          .order('created_at', { ascending: false })
          .limit(20);

        if (albums) {
          queryDetails.push(...albums.map((a: any) => ({
            ...a,
            type: 'album' as const,
            dj_name: (Array.isArray(a.dj_profiles) ? a.dj_profiles[0]?.dj_name : a.dj_profiles?.dj_name) || 'Unknown',
            status: 'active'
          })));
        }
      }

      setContent(queryDetails.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));

    } catch (err) {
      console.error('[LOAD_CONTENT_ERROR]', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string, type: 'track' | 'album') {
    if (!confirm('Are you sure you want to delete this permanently?')) return;
    try {
      const table = type === 'track' ? 'tracks' : 'album_packs';
      const { error } = await supabase.from(table).delete().eq('id', id);
      if (error) throw error;
      setContent(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      console.error('[DELETE_CONTENT_ERROR]', err);
    }
  }

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 space-y-8 animate-in fade-in duration-500">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-pink-500/10 rounded-2xl border border-pink-500/20 shadow-pink-glow">
              <Layers className="w-8 h-8 text-pink-400" />
            </div>
            <div>
              <h1 className="text-3xl font-heading font-bold text-white">Content Moderation</h1>
              <p className="text-zinc-400">Review and moderate all tracks and albums across the platform.</p>
            </div>
          </div>

          <div className="flex bg-zinc-900/50 p-1 rounded-xl border border-zinc-800">
            <button
              onClick={() => setTab('all')}
              className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all ${tab === 'all' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
            >
              All
            </button>
            <button
              onClick={() => setTab('tracks')}
              className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all ${tab === 'tracks' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
            >
              Tracks
            </button>
            <button
              onClick={() => setTab('albums')}
              className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all ${tab === 'albums' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-500 hover:text-white'}`}
            >
              Albums
            </button>
          </div>
        </div>

        <Card className="bg-zinc-950/50 border-zinc-900">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-white">Active Content Repository</CardTitle>
              <CardDescription>Most recent {content.length} items.</CardDescription>
            </div>
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-pink-400" size={14} />
              <input
                type="text"
                placeholder="Search by title..."
                className="bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-pink-500/50 transition-all w-48"
              />
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-4 animate-pulse">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div key={i} className="h-14 bg-zinc-900 rounded-xl" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-900 hover:bg-transparent">
                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Type</TableHead>
                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Title / DJ</TableHead>
                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Price</TableHead>
                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Uploaded</TableHead>
                    <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {content.map((item) => (
                    <TableRow key={item.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                      <TableCell>
                        {item.type === 'track' ? (
                          <div className="p-2 bg-blue-500/10 rounded-lg w-fit">
                            <Music size={14} className="text-blue-400" />
                          </div>
                        ) : (
                          <div className="p-2 bg-purple-500/10 rounded-lg w-fit">
                            <Layers size={14} className="text-purple-400" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <p className="text-sm font-bold text-white group-hover:text-pink-400 transition-colors uppercase tracking-tight">{item.title}</p>
                        <p className="text-[10px] text-zinc-500 font-black uppercase tracking-widest">{item.dj_name}</p>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-bold text-zinc-300">₹{item.price.toLocaleString()}</span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-zinc-600 font-medium">{new Date(item.created_at).toLocaleDateString()}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-lg">
                            <Play size={14} />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-lg">
                            <AlertTriangle size={14} />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleDelete(item.id, item.type)}
                            className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-lg"
                          >
                            <Trash2 size={14} />
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
