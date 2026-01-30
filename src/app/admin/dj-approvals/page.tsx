"use client";

import { supabase } from "@/app/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/app/components/RequireRole";

export default function DJApprovals() {
  const [requests, setRequests] = useState<any[]>([]);

  useEffect(() => {
    supabase
      .from("dj_profiles")
      .select("*")
      .eq("status", "pending")
      .then(({ data }) => setRequests(data || []));
  }, []);

  const approveDJ = async (id: string, userId: string) => {
    await supabase.from("dj_profiles").update({ status: "approved" }).eq("id", id);
    await supabase.from("profiles").update({ role: "dj" }).eq("id", userId);
    alert("DJ approved");
  };

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">DJ Applications</h1>

        {requests.map((dj) => (
          <div key={dj.id} className="mb-4 border p-3">
            <p><strong>{dj.dj_name}</strong></p>
            <p>{dj.bio}</p>
            <button
              className="bg-green-600 px-3 py-1 mt-2"
              onClick={() => approveDJ(dj.id, dj.user_id)}
            >
              Approve
            </button>
          </div>
        ))}
      </div>
    </RequireRole>
  );
}
