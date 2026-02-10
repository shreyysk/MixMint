'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { History, ShieldAlert, Globe, Clock } from 'lucide-react';

function formatRelativeTime(date: Date) {
    const diff = new Date().getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'just now';
}

interface LoginRecord {
    id: string;
    ip_address: string;
    user_agent: string;
    is_suspicious: boolean;
    created_at: string;
}

export function LoginHistory() {
    const [history, setHistory] = useState<LoginRecord[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHistory();
    }, []);

    async function fetchHistory() {
        setLoading(true);
        const { data, error } = await supabase
            .from('login_history')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(10);

        if (!error && data) {
            setHistory(data);
        }
        setLoading(false);
    }

    return (
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <History className="w-5 h-5 text-purple-400" />
                    Recent Login History
                </CardTitle>
                <CardDescription>
                    Monitor where you've logged in from recently.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Location / IP</TableHead>
                            <TableHead>Browser / OS</TableHead>
                            <TableHead>Time</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {history.map((record) => (
                            <TableRow key={record.id} className={record.is_suspicious ? 'bg-red-500/5' : ''}>
                                <TableCell>
                                    <div className="flex items-center gap-3">
                                        <Globe className="w-4 h-4 text-gray-400" />
                                        <div>
                                            <div className="font-medium text-white flex items-center gap-2">
                                                {record.ip_address}
                                                {record.is_suspicious && (
                                                    <ShieldAlert className="w-3 h-3 text-red-400" />
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell className="text-gray-400 text-xs max-w-[200px] truncate">
                                    {record.user_agent}
                                </TableCell>
                                <TableCell className="text-gray-400 text-sm whitespace-nowrap">
                                    <div className="flex items-center gap-2">
                                        <Clock className="w-3 h-3 text-gray-500" />
                                        {formatRelativeTime(new Date(record.created_at))}
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                        {history.length === 0 && !loading && (
                            <TableRow>
                                <TableCell colSpan={3} className="text-center py-8 text-gray-500">
                                    No login history available.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
