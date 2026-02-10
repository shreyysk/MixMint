'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck, XCircle, Monitor, Smartphone, Trash2 } from 'lucide-react';

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

interface Device {
    id: string;
    fingerprint: string;
    label: string;
    status: 'authorized' | 'revoked' | 'banned';
    last_ip: string;
    last_active_at: string;
    created_at: string;
}

export function DeviceManager() {
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDevices();
    }, []);

    async function fetchDevices() {
        setLoading(true);
        const { data, error } = await supabase
            .from('user_devices')
            .select('*')
            .order('last_active_at', { ascending: false });

        if (!error && data) {
            setDevices(data);
        }
        setLoading(false);
    }

    async function revokeDevice(id: string) {
        if (!confirm('Are you sure you want to revoke this device? You will be logged out on that device.')) return;

        const { error } = await supabase
            .from('user_devices')
            .update({ status: 'revoked' })
            .eq('id', id);

        if (!error) {
            fetchDevices();
        }
    }

    return (
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-purple-400" />
                    Device Management
                </CardTitle>
                <CardDescription>
                    You can have up to 3 authorized devices for downloads.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Device</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Last Active</TableHead>
                            <TableHead className="text-right">Action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {devices.map((device) => (
                            <TableRow key={device.id}>
                                <TableCell>
                                    <div className="flex items-center gap-3">
                                        {device.label.toLowerCase().includes('phone') ? (
                                            <Smartphone className="w-4 h-4 text-gray-400" />
                                        ) : (
                                            <Monitor className="w-4 h-4 text-gray-400" />
                                        )}
                                        <div>
                                            <div className="font-medium text-white">{device.label}</div>
                                            <div className="text-xs text-gray-500">{device.last_ip}</div>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    {device.status === 'authorized' ? (
                                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-400 rounded-full bg-green-400/10">
                                            Authorized
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-red-400 rounded-full bg-red-400/10">
                                            Revoked
                                        </span>
                                    )}
                                </TableCell>
                                <TableCell className="text-gray-400 text-sm">
                                    {formatRelativeTime(new Date(device.last_active_at))}
                                </TableCell>
                                <TableCell className="text-right">
                                    {device.status === 'authorized' && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => revokeDevice(device.id)}
                                            className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                        {devices.length === 0 && !loading && (
                            <TableRow>
                                <TableCell colSpan={4} className="text-center py-8 text-gray-500">
                                    No devices registered yet.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
