"use client";

import { useAuth } from "@/app/lib/AuthContext";
import { useUserRole } from "@/app/lib/useUserRole";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const { role, loading: roleLoading } = useUserRole(user?.id);

  if (loading || roleLoading) return <p>Loading...</p>;

  if (!user) return <p>You must be logged in.</p>;

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p>Email: {user.email}</p>
      <p>Role: {role}</p>
    </div>
  );
}
