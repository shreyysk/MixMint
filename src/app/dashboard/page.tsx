"use client";

import { useAuth } from "@/app/lib/AuthContext";

export default function DashboardPage() {
  const { user, loading } = useAuth();

  if (loading) return <p>Loading...</p>;

  if (!user) {
    return <p>You must be logged in to view this page.</p>;
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold">User Dashboard</h1>
      <p className="mt-2">Logged in as: {user.email}</p>
    </div>
  );
}
