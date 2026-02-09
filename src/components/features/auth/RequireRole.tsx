"use client";

import { useAuth } from "@/lib/AuthContext";
import { useUserRole } from "@/lib/useUserRole";

export default function RequireRole({
  allowed,
  children,
}: {
  allowed: Array<"user" | "dj" | "admin">;
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const { role, loading: roleLoading } = useUserRole(user?.id);

  if (loading || roleLoading) {
    return <p className="p-6">Loading...</p>;
  }

  if (!user) {
    return <p className="p-6">You must be logged in.</p>;
  }

  if (!role || !allowed.includes(role)) {
    return <p className="p-6">Access denied.</p>;
  }

  return <>{children}</>;
}
