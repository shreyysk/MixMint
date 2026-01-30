"use client";

import { useEffect, useState } from "react";
import { supabase } from "./supabaseClient";

export function useUserRole(userId?: string) {
  const [role, setRole] = useState<"user" | "dj" | "admin" | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchRole = async () => {
      const { data, error } = await supabase
        .from("profiles")
        .select("role")
        .eq("id", userId)
        .single();

      if (!error && data) {
        setRole(data.role);
      }

      setLoading(false);
    };

    fetchRole();
  }, [userId]);

  return { role, loading };
}
