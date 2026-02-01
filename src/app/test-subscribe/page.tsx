"use client";

import { supabase } from "@/app/lib/supabaseClient";

export default function TestSubscribe() {
  async function subscribe() {
    const sessionResult = await supabase.auth.getSession();
    console.log("SESSION RESULT:", sessionResult);

    const session = sessionResult.data.session;

    if (!session) {
      alert("No session found. Please login again.");
      return;
    }

    alert("Session found. Calling API...");

    const res = await fetch("/api/subscribe", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        dj_id: "d68c0c87-b171-4231-8876-2a06ee1e3f8c",
        plan: "basic",
      }),
    });

    alert(JSON.stringify(await res.json()));
  }

  return (
    <div className="p-6">
      <button
        onClick={subscribe}
        className="bg-purple-600 px-4 py-2 rounded"
      >
        Subscribe (TEST)
      </button>
    </div>
  );
}