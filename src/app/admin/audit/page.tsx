"use client";

import { useEffect, useState } from "react";
import RequireRole from "@/components/features/auth/RequireRole";
import { supabase } from "@/lib/supabaseClient";
import { Loader2, Search, Filter, ShieldAlert } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

interface AuditLog {
    id: string;
    admin_id: string;
    action_type: string;
    entity_type: string;
    entity_id: string | null;
    details: any;
    ip_address: string | null;
    created_at: string;
    admin_email?: string; // We'll join this manually or via view
}

export default function AdminAuditPage() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterAction, setFilterAction] = useState("");
    const [filterEntity, setFilterEntity] = useState("");

    useEffect(() => {
        fetchLogs();
    }, []);

    async function fetchLogs() {
        setLoading(true);
        try {
            let query = supabase
                .from('admin_audit_logs')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(100);

            if (filterAction) {
                query = query.eq('action_type', filterAction);
            }
            if (filterEntity) {
                query = query.eq('entity_type', filterEntity);
            }

            const { data, error } = await query;
            if (error) throw error;

            // Fetch admin emails (basic join simulation)
            // In a real app we'd use a view or proper relation if setup
            // For now, let's just display IDs or fetch profiles if needed. 
            // We can do a second query for unique admin_ids.

            setLogs(data || []);

        } catch (err) {
            console.error("Failed to fetch logs:", err);
        } finally {
            setLoading(false);
        }
    }

    return (
        <RequireRole allowed={["admin"]}>
            <div className="p-8 text-white min-h-screen">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-black uppercase flex items-center gap-3">
                        <ShieldAlert className="text-mint-studio" />
                        Audit Logs
                    </h1>
                    <Button onClick={fetchLogs} variant="outline" size="sm">Refresh</Button>
                </div>

                {/* Filters */}
                <div className="flex gap-4 mb-6 bg-zinc-900/50 p-4 rounded-xl border border-zinc-800">
                    <div className="flex items-center gap-2 flex-1">
                        <Filter size={16} className="text-zinc-500" />
                        <Input
                            placeholder="Filter by Action (e.g., ban_user)"
                            value={filterAction}
                            onChange={(e) => setFilterAction(e.target.value)}
                            className="bg-transparent border-none h-8 text-sm"
                        />
                    </div>
                    <div className="w-px bg-zinc-800" />
                    <div className="flex items-center gap-2 flex-1">
                        <Filter size={16} className="text-zinc-500" />
                        <Input
                            placeholder="Filter by Entity (e.g., user, track)"
                            value={filterEntity}
                            onChange={(e) => setFilterEntity(e.target.value)}
                            className="bg-transparent border-none h-8 text-sm"
                        />
                    </div>
                    <Button onClick={fetchLogs} size="sm">Apply</Button>
                </div>

                {/* Logs Table */}
                <div className="rounded-xl border border-zinc-800 overflow-hidden bg-zinc-900/30">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-zinc-900 text-zinc-500 font-bold uppercase text-xs">
                                <tr>
                                    <th className="p-4">Time</th>
                                    <th className="p-4">Admin ID</th>
                                    <th className="p-4">Action</th>
                                    <th className="p-4">Entity</th>
                                    <th className="p-4">Details</th>
                                    <th className="p-4">IP</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-800">
                                {loading ? (
                                    <tr>
                                        <td colSpan={6} className="p-8 text-center text-zinc-500">
                                            <Loader2 className="animate-spin mx-auto mb-2" />
                                            Loading logs...
                                        </td>
                                    </tr>
                                ) : logs.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="p-8 text-center text-zinc-500">
                                            No logs found.
                                        </td>
                                    </tr>
                                ) : (
                                    logs.map((log) => (
                                        <tr key={log.id} className="hover:bg-zinc-800/50 transition-colors">
                                            <td className="p-4 whitespace-nowrap text-zinc-400">
                                                {new Date(log.created_at).toLocaleString()}
                                            </td>
                                            <td className="p-4 font-mono text-xs text-zinc-500" title={log.admin_id}>
                                                {log.admin_id.slice(0, 8)}...
                                            </td>
                                            <td className="p-4">
                                                <span className="px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">
                                                    {log.action_type}
                                                </span>
                                            </td>
                                            <td className="p-4 text-zinc-300">
                                                {log.entity_type} {log.entity_id ? `(${log.entity_id.slice(0, 6)}...)` : ''}
                                            </td>
                                            <td className="p-4 text-zinc-500 text-xs max-w-xs truncate">
                                                {JSON.stringify(log.details)}
                                            </td>
                                            <td className="p-4 text-zinc-600 text-xs text-right">
                                                {log.ip_address || 'N/A'}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </RequireRole>
    );
}
