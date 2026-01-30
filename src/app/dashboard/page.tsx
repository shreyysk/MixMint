"use client";

import RequireRole from "@/app/components/RequireRole";

export default function DashboardPage() {
  return (
    <RequireRole allowed={["user", "dj", "admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold">User Dashboard</h1>
        <p>Welcome to MixMint.</p>
      </div>
    </RequireRole>
  );
}