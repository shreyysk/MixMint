'use client';

import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import RequireRole from "@/components/features/auth/RequireRole";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import {
    Users,
    ShieldCheck,
    ShieldAlert,
    UserCog,
    RefreshCw,
    Search,
    Shield
} from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';

interface UserWithRole {
    id: string;
    email: string;
    role: 'admin' | 'moderator' | 'dj' | 'user';
    full_name: string;
    avatar_url: string;
}

export default function UserRoleManagement() {
    const [users, setUsers] = useState<UserWithRole[]>([]);
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
                .limit(50);

            if (error) throw error;
            setUsers(data || []);
        } catch (err) {
            console.error('[LOAD_USERS_ERROR]', err);
        } finally {
            setLoading(false);
        }
    }

    async function updateRole(userId: string, newRole: string) {
        try {
            const { error } = await supabase
                .from('profiles')
                .update({ role: newRole })
                .eq('id', userId);

            if (error) throw error;
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole as any } : u));
        } catch (err) {
            console.error('[UPDATE_ROLE_ERROR]', err);
        }
    }

    const filteredUsers = users.filter(u =>
        u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.full_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-6 space-y-8 animate-in fade-in duration-500">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-blue-glow">
                            <Shield className="w-8 h-8 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-heading font-bold text-white">RBAC & Role Manager</h1>
                            <p className="text-zinc-400">Manage platform permissions and assign administrative privileges.</p>
                        </div>
                    </div>

                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-blue-500 transition-colors" size={18} />
                        <input
                            type="text"
                            placeholder="Find user by name/email..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="bg-zinc-900 border border-zinc-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500/50 transition-all w-full md:w-80"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <Card className="bg-zinc-950/20 border-blue-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <ShieldCheck className="w-5 h-5 text-blue-400" />
                                <span className="text-xs font-black uppercase tracking-widest text-zinc-500">Admins</span>
                            </div>
                            <p className="text-3xl font-bold text-white">{users.filter(u => u.role === 'admin').length || 1}</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-zinc-950/20 border-purple-500/10">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <UserCog className="w-5 h-5 text-purple-400" />
                                <span className="text-xs font-black uppercase tracking-widest text-zinc-500">Moderators</span>
                            </div>
                            <p className="text-3xl font-bold text-white">{users.filter(u => u.role === 'moderator').length}</p>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-zinc-950/50 border-zinc-900 overflow-hidden">
                    <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-900">
                        <div>
                            <CardTitle className="text-white">Active Permissions Matrix</CardTitle>
                            <CardDescription>Assign roles to grant specific platform capabilities.</CardDescription>
                        </div>
                        <Button variant="ghost" size="sm" onClick={loadUsers} className="text-zinc-500 hover:text-white">
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow className="border-zinc-900 hover:bg-transparent px-4">
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest pl-6">Profile</TableHead>
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Email</TableHead>
                                    <TableHead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">Current Role</TableHead>
                                    <TableHead className="text-right text-zinc-500 text-[10px] font-black uppercase tracking-widest pr-6">Management</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredUsers.map((user) => (
                                    <TableRow key={user.id} className="border-zinc-900 hover:bg-zinc-900/40 transition-colors group">
                                        <TableCell className="pl-6">
                                            <div className="flex items-center gap-3">
                                                <Avatar src={user.avatar_url} fallback={user.full_name?.[0]} className="w-10 h-10 border border-zinc-800" />
                                                <p className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors tracking-tight">{user.full_name || 'Anonymous User'}</p>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <p className="text-xs text-zinc-500 font-medium">{user.email}</p>
                                        </TableCell>
                                        <TableCell>
                                            <span className={`px-2 py-0.5 rounded-full text-[8px] font-black uppercase tracking-widest border ${user.role === 'admin' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                    user.role === 'moderator' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                                                        user.role === 'dj' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                                            'bg-zinc-800 text-zinc-500 border-zinc-700'
                                                }`}>
                                                {user.role || 'user'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-right pr-6">
                                            <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 text-[10px] font-black uppercase tracking-widest hover:text-blue-400"
                                                    onClick={() => updateRole(user.id, 'admin')}
                                                >
                                                    Admin
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 text-[10px] font-black uppercase tracking-widest hover:text-purple-400"
                                                    onClick={() => updateRole(user.id, 'moderator')}
                                                >
                                                    Mod
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 text-[10px] font-black uppercase tracking-widest hover:text-white"
                                                    onClick={() => updateRole(user.id, 'user')}
                                                >
                                                    Revoke
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </RequireRole>
    );
}
