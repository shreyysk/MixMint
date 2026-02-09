
import { supabaseAdmin } from "@/lib/supabaseServer";

export class TrackService {
  /**
   * Get tracks and albums for a DJ
   */
  static async getByDjId(djId: string) {
    const { data: tracks, error: tracksError } = await supabaseAdmin
        .from("tracks")
        .select("id, title, price, created_at, status, file_key, youtube_url, is_fan_only")
        .eq("dj_id", djId)
        .order("created_at", { ascending: false })
        .limit(100);

    const { data: albumPacks, error: albumsError } = await supabaseAdmin
        .from("album_packs")
        .select("id, title, price, created_at, description")
        .eq("dj_id", djId)
        .order("created_at", { ascending: false })
        .limit(100);

    if (tracksError || albumsError) {
        throw new Error(tracksError?.message || albumsError?.message);
    }

    return {
        tracks: tracks || [],
        albumPacks: albumPacks || []
    };
  }
}
