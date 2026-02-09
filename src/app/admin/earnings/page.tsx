
"use client";

import { supabase } from "@/app/lib/supabaseClient";
import { useEffect, useState } from "react";
import RequireRole from "@/app/components/RequireRole";

interface DJEarnings {
  dj_id: string;
  dj_name: string;
  total_earnings: number;
}

export default function DJEarningsPage() {
  const [earnings, setEarnings] = useState<DJEarnings[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEarnings();
  }, []);

  async function fetchEarnings() {
    setLoading(true);

    // This is inefficient and should be done in a Supabase RPC function
    // but for the sake of this demo, we'll do it on the client-side.

    const { data: djs, error: djsError } = await supabase
      .from('dj_profiles')
      .select('id, dj_name');

    const { data: purchases, error: purchasesError } = await supabase
      .from('purchases')
      .select('content_id, content_type, amount')
      .eq('status', 'successful');

    const { data: tracks, error: tracksError } = await supabase.from('tracks').select('id, dj_id');
    const { data: albums, error: albumsError } = await supabase.from('album_packs').select('id, dj_id');

    const contentToDjMap = new Map<string, string>();
    (tracks || []).forEach(t => contentToDjMap.set(`track_${t.id}`, t.dj_id));
    (albums || []).forEach(a => contentToDjMap.set(`zip_${a.id}`, a.dj_id));

    const earningsMap: { [key: string]: number } = {};

    for (const purchase of (purchases || [])) {
      const mapKey = `${purchase.content_type}_${purchase.content_id}`;
      const djId = contentToDjMap.get(mapKey);
      if (djId) {
        earningsMap[djId] = (earningsMap[djId] || 0) + purchase.amount;
      }
    }

    const djEarnings = (djs || []).map(dj => ({
      dj_id: dj.id,
      dj_name: dj.dj_name,
      total_earnings: earningsMap[dj.id] || 0,
    }));

    setEarnings(djEarnings);
    setLoading(false);
  }

  return (
    <RequireRole allowed={["admin"]}>
      <div className="p-6 text-white">
        <h1 className="text-2xl font-bold mb-4">DJ Earnings</h1>

        {loading ? (
          <p>Loading earnings...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-700">
              <thead className="bg-zinc-800">
                <tr>
                  <th scope="col" className="py-3.5 px-4 text-left text-sm font-semibold text-white">
                    DJ Name
                  </th>
                  <th scope="col" className="py-3.5 px-4 text-left text-sm font-semibold text-white">
                    Total Earnings
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 bg-zinc-900">
                {earnings.map((dj) => (
                  <tr key={dj.dj_id}>
                    <td className="whitespace-nowrap py-4 px-4 text-sm font-medium text-white">
                      {dj.dj_name}
                    </td>
                    <td className="whitespace-nowrap py-4 px-4 text-sm text-zinc-400">
                      ₹{dj.total_earnings / 100}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </RequireRole>
  );
}
