
"use client";

import { supabase } from "../../../lib/supabaseClient";
import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "../../components/ui/Card";
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/Avatar";
import RequireRole from "../../components/RequireRole";

interface DJRequest {
    id: string;
    user_id: string;
    dj_name: string;
    bio: string;
    profile_picture_url: string;
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
            .select("id, user_id, dj_name, bio, profile_picture_url")
            .eq("status", "pending");
        
        if (error) {
            console.error("Error fetching DJ requests:", error);
        } else {
            setRequests(data || []);
        }
        setLoading(false);
    }

    const handleApprove = async (id: string, userId: string) => {
        // Update dj_profiles table
        const { error: profileError } = await supabase.from("dj_profiles").update({ status: "approved" }).eq("id", id);
        if (profileError) {
            alert("Error updating DJ profile status.");
            return;
        }

        // Update profiles table to assign 'dj' role
        const { error: roleError } = await supabase.from("profiles").update({ role: "dj" }).eq("id", userId);
        if (roleError) {
            alert("Error assigning DJ role.");
            return;
        }

        alert("DJ approved successfully!");
        fetchRequests(); // Re-fetch to update the list
    };

     const handleReject = async (id: string) => {
        // Update status to 'rejected' in dj_profiles table
        const { error } = await supabase.from("dj_profiles").update({ status: "rejected" }).eq("id", id);
        if (error) {
            alert("Error rejecting DJ application.");
        } else {
            alert("DJ application rejected.");
            fetchRequests(); // Re-fetch to update the list
        }
    };

    return (
        <RequireRole allowed={["admin"]}>
            <div className="min-h-screen pb-24">
                 <div className="px-6 md:px-12">
                    <div className="max-w-7xl mx-auto">
                        <h1 className="text-4xl md:text-5xl font-bold text-white mb-10">DJ Applications</h1>

                        {loading ? (
                            <p className="text-zinc-400">Loading applications...</p>
                        ) : requests.length === 0 ? (
                            <p className="text-zinc-400">No pending DJ applications.</p>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {requests.map((dj) => (
                                    <Card key={dj.id}>
                                        <CardHeader className="flex items-center gap-4">
                                            <Avatar>
                                                <AvatarImage src={dj.profile_picture_url} alt={dj.dj_name} />
                                                <AvatarFallback>{dj.dj_name.charAt(0)}</AvatarFallback>
                                            </Avatar>
                                            <div>
                                                <CardTitle>{dj.dj_name}</CardTitle>
                                            </div>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-zinc-400 text-sm line-clamp-3">{dj.bio}</p>
                                        </CardContent>
                                        <CardFooter className="flex justify-end gap-2">
                                            <Button variant="outline" onClick={() => handleReject(dj.id)}>Reject</Button>
                                            <Button onClick={() => handleApprove(dj.id, dj.user_id)}>Approve</Button>
                                        </CardFooter>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </RequireRole>
    );
}
