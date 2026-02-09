
"use client";

import { supabase } from "@/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/components/features/auth/RequireRole";
import { Button } from "@/components/ui/Button";

interface DJProfile {
  id: string;
  dj_name: string;
  featured: boolean;
}

export default function FeaturedDJs() {
  const [djs, setDjs] = useState<DJProfile[]>([]);

  useEffect(() => {
    fetchDJs();
  }, []);

  async function fetchDJs() {
    const { data } = await supabase.from("dj_profiles").select("id, dj_name, featured");
    setDjs(data || []);
  }

  const toggleFeatured = async (dj: DJProfile) => {
    await supabase.from("dj_profiles").update({ featured: !dj.featured }).eq("id", dj.id);
    alert(`DJ ${dj.dj_name} ${!dj.featured ? 'featured' : 'unfeatured'}`);
    fetchDJs();
  };

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">Featured DJs</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {djs.map((dj) => (
            <div key={dj.id} className="border p-3 rounded-lg flex items-center justify-between">
              <p className="font-bold">{dj.dj_name}</p>
              <Button
                onClick={() => toggleFeatured(dj)}
                variant={dj.featured ? "secondary" : "primary"}
                size="sm"
              >
                {dj.featured ? 'Unfeature' : 'Feature'}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </RequireRole>
  );
}
