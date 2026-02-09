
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// TODO: Set up environment variables
const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY!;

export default async (req: Request): Promise<Response> => {
  // Ensure the request is authorized (e.g., check for admin role)
  // This is a simplified example; in production, use a more robust auth check
  const authHeader = req.headers.get('Authorization');
  if (!authHeader) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey);

  try {
    // Fetch all DJs
    const { data: djs, error: djsError } = await supabase
      .from('dj_profiles')
      .select('id, dj_name');

    if (djsError) throw djsError;

    // Fetch all successful purchases
    const { data: purchases, error: purchasesError } = await supabase
      .from('purchases')
      .select('content_id, content_type, amount')
      .eq('status', 'successful');

    if (purchasesError) throw purchasesError;

    // Fetch all tracks and albums to map content to DJs
    const { data: tracks, error: tracksError } = await supabase.from('tracks').select('id, dj_id');
    if (tracksError) throw tracksError;

    const { data: albums, error: albumsError } = await supabase.from('album_packs').select('id, dj_id');
    if (albumsError) throw albumsError;

    const contentToDjMap = new Map<string, string>();
    tracks.forEach(t => contentToDjMap.set(`track_${t.id}`, t.dj_id));
    albums.forEach(a => contentToDjMap.set(`zip_${a.id}`, a.dj_id));

    // Calculate earnings
    const earnings: { [key: string]: number } = {};

    for (const purchase of purchases) {
      const mapKey = `${purchase.content_type}_${purchase.content_id}`;
      const djId = contentToDjMap.get(mapKey);
      if (djId) {
        earnings[djId] = (earnings[djId] || 0) + purchase.amount;
      }
    }

    // Format the final response
    const djEarnings = djs.map(dj => ({
      dj_id: dj.id,
      dj_name: dj.dj_name,
      total_earnings: earnings[dj.id] || 0,
    }));

    return new Response(JSON.stringify(djEarnings), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
};
