'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Users, Shield, Ban, CheckCircle, MoreVertical, Search } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import RequireRole from "@/components/features/auth/RequireRole";
import { ExportButton } from '@/components/ui/ExportButton';

interface UserProfile {
    id: string;
    full_name: string;
    role: 'user' | 'dj' | 'admin';
    avatar_url: string;
    is_banned: boolean;
    created_at: string;
}

export default function UserManagementPage() {
    const [users, setUsers] = useState<UserProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadUsers();
    }, []);

    async function loadUsers() {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('profiles')
                .select('*')
                .order('created_at', { ascending: false });

            if (error) throw error;
            setUsers(data || []);
        } catch (err) {
            console.error('[LOAD_USERS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function toggleBan(id: string, currentStatus: boolean) {
        try {
            const { error } = await supabase
                .from('profiles')
                .update({ is_banned: !currentStatus })
                .eq('id', id);

            if (error) throw error;
            setUsers(prev => prev.map(u => u.id === id ? { ...u, is_banned: !currentStatus } : u));
        } catch (err) {
            console.error('[TOGGLE_BAN_ERROR]', err);
        }
    }

    async function changeRole(id: string, newRole: 'user' | 'dj' | 'admin') {
        try {
            const { error } = await supabase
                .from('profiles')
                .update({ role: newRole })
                .eq('id', id);

            if (error) throw error;
            setUsers(prev => prev.map(u => u.id === id ? { ...u, role: newRole } : u));
        } catch (err) {
            console.error('[CHANGE_ROLE_ERROR]', err);
        }
    }

    const filteredUsers = users.filter(u =>
        u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.role.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <RequireRole allowed={["admin"]}>
            <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-blue-glow">
                            <Users className="w-8 h-8 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">User Management</h1>
                            <p className="text-zinc-400">Manage user accounts, roles, and platform access.</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <ExportButton
                            data={users.map(u => ({
                                name: u.full_name,
                                role: u.role,
                                joined: u.created_at,
                                status: u.is_banned ? 'banned' : 'active'
                            }))}
                            filename="mixmint_users"
                        />
                        <div className="relative group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-blue-400 transition-colors" size={18} />
                            <input
                                type="text"
                                placeholder="Search users or roles..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="bg-zinc-900 border border-zinc-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-all w-full md:w-64"
                            />
                        </div>
                    </div>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-800">
                    <CardHeader>
                        <CardTitle className="text-white">All Users</CardTitle>
                        <CardDescription>
                            Review activity and adjust permissions for {users.length} registered users.
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
                                        <TableHead>User</TableHead>
                                        <TableHead>Role</TableHead>
                                        <TableHead>Joined</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredUsers.map((u) => (
                                        <TableRow key={u.id} className={u.is_banned ? "opacity-50" : ""}>
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Avatar src={u.avatar_url} fallback={u.full_name[0]} className="w-8 h-8" />
                                                    <span className="font-medium text-white">{u.full_name}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <select
                                                    value={u.role}
                                                    onChange={(e) => changeRole(u.id, e.target.value as any)}
                                                    className="bg-zinc-900 border border-zinc-800 rounded-lg px-2 py-1 text-xs text-zinc-300 focus:outline-none"
                                                >
                                                    <option value="user">User</option>
                                                    <option value="dj">DJ</option>
                                                    <option value="admin">Admin</option>
                                                </select>
                                            </TableCell>
                                            <TableCell className="text-zinc-500 text-xs">
                                                {new Date(u.created_at).toLocaleDateString()}
                                            </TableCell>
                                            <TableCell>
                                                {u.is_banned ? (
                                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-[10px] font-black text-red-400 uppercase tracking-widest">
                                                        <Ban className="w-3 h-3" />
                                                        Banned
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20 text-[10px] font-black text-green-400 uppercase tracking-widest">
                                                        <CheckCircle className="w-3 h-3" />
                                                        Active
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => toggleBan(u.id, u.is_banned)}
                                                    className={u.is_banned ? "text-green-400 hover:text-green-300" : "text-red-400 hover:text-red-300"}
                                                >
                                                    {u.is_banned ? "Unban" : "Ban User"}
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
