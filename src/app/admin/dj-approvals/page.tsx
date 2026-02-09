
"use client";

import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import RequireRole from "@/components/features/auth/RequireRole";
import { Check, X, User } from "lucide-react";

interface DJRequest {
    id: string; // This is the User ID in my schema
    dj_name: string;
    bio: string;
    status: 'pending' | 'approved' | 'rejected';
}

export default function DJApprovals() {
    const [requests, setRequests] = useState<DJRequest[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchRequests();
    }, []);

    async function fetchRequests() {
        setLoading(true);
        const { data, error } = await supabase
            .from("dj_profiles")
            .select("id, dj_name, bio, status")
            .eq("status", "pending");

        if (error) {
            console.error("Error fetching DJ requests:", error);
        } else {
            setRequests(data || []);
        }
        setLoading(false);
    }

    const handleApprove = async (id: string) => {
        try {
            // 1. Update dj_profiles status
            const { error: profileError } = await supabase
                .from("dj_profiles")
                .update({ status: "approved" })
                .eq("id", id);

            if (profileError) throw profileError;

            // 2. Update core profile role
            const { error: roleError } = await supabase
                .from("profiles")
                .update({ role: "dj" })
                .eq("id", id);

            if (roleError) throw roleError;

            alert("DJ approved successfully!");
            fetchRequests();
        } catch (err: any) {
            alert(`Approval failed: ${err.message}`);
        }
    };

    const handleReject = async (id: string) => {
        const { error } = await supabase
            .from("dj_profiles")
            .update({ status: "rejected" })
            .eq("id", id);

        if (error) {
            alert("Error rejecting DJ application.");
        } else {
            alert("DJ application rejected.");
            fetchRequests();
        }
    };

    return (
        <RequireRole allowed={["admin"]}>
            <div className="min-h-screen py-24 bg-black text-white">
                <div className="px-6 md:px-12 max-w-7xl mx-auto">
                    <div className="mb-10">
                        <h1 className="text-4xl font-black uppercase tracking-tight text-white mb-2">
                            DJ Partner Approvals
                        </h1>
                        <p className="text-zinc-500">Review and authorize new DJ applicants for the MixMint platform.</p>
                    </div>

                    <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-3xl overflow-hidden backdrop-blur-sm">
                        {loading ? (
                            <div className="p-20 text-center text-zinc-500">Loading pending applications...</div>
                        ) : requests.length === 0 ? (
                            <div className="p-20 text-center">
                                <User size={48} className="mx-auto mb-4 text-zinc-800" />
                                <p className="text-zinc-500 font-medium">No pending DJ applications at the moment.</p>
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>DJ Name</TableHead>
                                        <TableHead>Biography</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {requests.map((dj) => (
                                        <TableRow key={dj.id}>
                                            <TableCell className="font-bold text-white">{dj.dj_name}</TableCell>
                                            <TableCell className="max-w-md truncate text-zinc-400">{dj.bio}</TableCell>
                                            <TableCell className="text-right">
                                                <div className="flex justify-end gap-2">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleReject(dj.id)}
                                                        className="border-zinc-800 hover:bg-red-950/20 hover:text-red-500"
                                                    >
                                                        <X size={16} className="mr-1" /> Reject
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleApprove(dj.id)}
                                                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                                                    >
                                                        <Check size={16} className="mr-1" /> Approve
                                                    </Button>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </div>
                </div>
            </div>
        </RequireRole>
    );
}
