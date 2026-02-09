"use client";

import { useAuth } from "@/lib/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useState } from "react";
import { ShieldCheck, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

export default function FixRolePage() {
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);
    const [currentRole, setCurrentRole] = useState<string | null>("checking...");
    const [djProfileStatus, setDjProfileStatus] = useState<string | null>("checking...");
    const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

    // Fetch current status on load
    useState(() => {
        if (user) {
            supabase.from("profiles").select("role").eq("id", user.id).single()
                .then(({ data }) => setCurrentRole(data?.role || "none"));

            supabase.from("dj_profiles").select("status").eq("user_id", user.id).single()
                .then(({ data }) => setDjProfileStatus(data?.status || "missing"));
        }
    });

    const grantDJRole = async () => {
        if (!user) return;
        setLoading(true);
        setResult(null);

        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) throw new Error("Session expired. Please login again.");

            const res = await fetch("/api/dj/activate", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${session.access_token}`,
                },
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Activation failed");

            setResult({ type: "success", message: "DJ Role & Approved Profile granted! You are now a fully activated DJ." });

            // Re-fetch diagnostics
            const { data: p } = await supabase.from("profiles").select("role").eq("id", user.id).single();
            const { data: d } = await supabase.from("dj_profiles").select("status").eq("user_id", user.id).single();
            setCurrentRole(p?.role || "none");
            setDjProfileStatus(d?.status || "missing");

        } catch (err: any) {
            setResult({ type: "error", message: err.message || "Failed to update role." });
        } finally {
            setLoading(false);
        }
    };

    if (!user) {
        return (
            <div className="min-h-screen bg-[#050505] flex items-center justify-center p-6">
                <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-2xl flex items-center gap-3">
                    <AlertCircle className="text-red-400" />
                    <p className="text-red-400">Please login first to use this tool.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-[#111] border border-white/10 rounded-3xl p-8 shadow-2xl">
                <div className="w-16 h-16 bg-purple-600 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-purple-600/20">
                    <ShieldCheck className="w-8 h-8" />
                </div>

                <h1 className="text-2xl font-bold mb-2">DJ Role Activator</h1>
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-6 space-y-2">
                    <p className="text-xs text-gray-500 uppercase font-bold tracking-wider">Current Session</p>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">User ID:</span>
                        <span className="font-mono text-purple-400">{user.id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Email:</span>
                        <span className="text-white">{user.email}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Database Role:</span>
                        <span className={`font-bold transition-all ${currentRole === "dj" ? "text-green-400" : "text-yellow-500"}`}>{currentRole}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">DJ Profile Status:</span>
                        <span className={`font-bold transition-all ${djProfileStatus === "approved" ? "text-green-400" : "text-blue-400"}`}>{djProfileStatus}</span>
                    </div>
                </div>

                <p className="text-gray-400 text-sm mb-8 leading-relaxed">
                    This utility will assign the **DJ Role** to your account in the database.
                    Use this to unlock the Upload Portal and Content Manager.
                </p>

                {result && (
                    <div className={`p-4 rounded-xl flex items-start gap-3 mb-6 animate-in fade-in slide-in-from-top-2 ${result.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}>
                        {result.type === "success" ? <CheckCircle2 className="w-5 h-5 mt-0.5" /> : <AlertCircle className="w-5 h-5 mt-0.5" />}
                        <p className="text-sm font-medium leading-normal">{result.message}</p>
                    </div>
                )}

                <button
                    onClick={grantDJRole}
                    disabled={loading}
                    className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all ${loading
                        ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                        : "bg-purple-600 text-white hover:bg-purple-500 shadow-xl shadow-purple-600/20 active:scale-[0.98]"
                        }`}
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Processing...
                        </>
                    ) : (
                        "Grant Me DJ Role"
                    )}
                </button>

                {result?.type === "success" && (
                    <a
                        href="/dj/upload"
                        className="block text-center mt-6 text-purple-400 hover:text-purple-300 text-sm font-semibold transition-colors underline decoration-purple-400/30 underline-offset-4"
                    >
                        Go to Upload Portal →
                    </a>
                )}
            </div>
        </div>
    );
}
