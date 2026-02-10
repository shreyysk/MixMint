'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    FlaskConical,
    Plus,
    Play,
    Square,
    TrendingUp,
    Target,
    BarChart3,
    MoreVertical,
    RefreshCw,
    CheckCircle2,
    History
} from 'lucide-react';

interface Experiment {
    id: string;
    name: string;
    description: string;
    status: 'draft' | 'running' | 'concluded';
    conversion_goal: string;
    created_at: string;
    config: any;
}

export default function ExperimentsPage() {
    const [experiments, setExperiments] = useState<Experiment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadExperiments();
    }, []);

    async function loadExperiments() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('experiments')
                .select('*')
                .order('created_at', { ascending: false });

            if (error) throw error;
            setExperiments(data || []);
        } catch (err) {
            console.error('[LOAD_EXPERIMENTS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function toggleStatus(id: string, currentStatus: string) {
        const nextStatus = currentStatus === 'running' ? 'concluded' : 'running';
        try {
            const { error } = await supabase
                .from('experiments')
                .update({ status: nextStatus })
                .eq('id', id);

            if (error) throw error;
            setExperiments(prev => prev.map(e => e.id === id ? { ...e, status: nextStatus as any } : e));
        } catch (err) {
            console.error('[TOGGLE_EXP_STATUS_ERROR]', err);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-purple-glow">
                            <FlaskConical className="w-8 h-8 text-purple-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">Experiments & A/B Testing</h1>
                            <p className="text-zinc-400">Deploy and monitor platform variations to optimize conversion.</p>
                        </div>
                    </div>

                    <Button className="bg-purple-600 hover:bg-purple-500 text-white rounded-xl shadow-purple-glow gap-2 px-6">
                        <Plus size={18} />
                        Create Experiment
                    </Button>
                </div>

                {/* Experiment Metrics Overview */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="bg-zinc-950/20 border-emerald-500/10">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-emerald-500/10 rounded-xl">
                                <Play className="w-6 h-6 text-emerald-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Active Trials</p>
                                <p className="text-2xl font-bold text-white">4</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-purple-500/10">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-purple-500/10 rounded-xl">
                                <Target className="w-6 h-6 text-purple-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Conversion Uplift</p>
                                <p className="text-2xl font-bold text-white">+12.4%</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-blue-500/10">
                        <CardContent className="pt-6 flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-xl">
                                <History className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <p className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Completed Runs</p>
                                <p className="text-2xl font-bold text-white">18</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-white">Active & Draft Experiments</CardTitle>
                            <CardDescription>Monitor and manage your A/B test configurations.</CardDescription>
                        </div>
                        <Button variant="ghost" size="sm" onClick={loadExperiments}>
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="space-y-4 animate-pulse">
                                {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-20 bg-zinc-900 rounded-2xl" />)}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {experiments.map((exp) => (
                                    <div key={exp.id} className="p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl hover:border-purple-500/30 transition-all group">
                                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-3">
                                                    <h3 className="text-lg font-bold text-white group-hover:text-purple-400 transition-colors">{exp.name}</h3>
                                                    <span className={`px-2 py-0.5 rounded-full text-[8px] font-black uppercase tracking-widest border ${exp.status === 'running' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                                            exp.status === 'concluded' ? 'bg-zinc-800 text-zinc-500 border-zinc-700' :
                                                                'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                                        }`}>
                                                        {exp.status}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-zinc-400 max-w-xl">{exp.description}</p>
                                                <div className="flex items-center gap-6 mt-3 text-[10px] font-black uppercase tracking-widest text-zinc-600">
                                                    <span className="flex items-center gap-1.5"><Target size={12} className="text-purple-500" /> Goal: {exp.conversion_goal}</span>
                                                    <span className="flex items-center gap-1.5"><TrendingUp size={12} className="text-emerald-500" /> Confidence: 94%</span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                <Button
                                                    onClick={() => toggleStatus(exp.id, exp.status)}
                                                    size="sm"
                                                    className={`rounded-xl gap-2 font-bold uppercase tracking-widest text-[10px] ${exp.status === 'running' ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                                                        }`}
                                                >
                                                    {exp.status === 'running' ? <Square size={14} /> : <Play size={14} />}
                                                    {exp.status === 'running' ? 'Stop' : 'Launch'}
                                                </Button>
                                                <Button size="sm" variant="ghost" className="text-zinc-500 hover:text-white rounded-xl">
                                                    <BarChart3 size={18} />
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {experiments.length === 0 && (
                                    <div className="text-center py-20 border border-dashed border-zinc-900 rounded-3xl">
                                        <FlaskConical className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                                        <p className="text-zinc-500 font-bold uppercase tracking-widest text-xs">No experiments found.</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
