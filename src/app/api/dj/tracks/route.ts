import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";

export async function GET(req: Request) {
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.replace("Bearer ", "");

    const { data: userData } = await supabaseServer.auth.getUser(token);

    if (!userData?.user) {
        return NextResponse.json({ error: "Invalid user" }, { status: 401 });
    }

    const { data: dj } = await supabaseServer
        .from("dj_profiles")
        .select("id")
        .eq("user_id", userData.user.id)
        .eq("status", "approved")
        .single();

    if (!dj) {
        return NextResponse.json({ error: "Not a DJ" }, { status: 403 });
    }

    const { data: tracks, error: tracksError } = await supabaseServer
        .from("tracks")
        .select("id, title, price, created_at")
        .eq("dj_id", dj.id)
        .order("created_at", { ascending: false });

    const { data: albumPacks, error: albumsError } = await supabaseServer
        .from("album_packs")
        .select("id, title, price, created_at, description")
        .eq("dj_id", dj.id)
        .order("created_at", { ascending: false });

    if (tracksError || albumsError) {
        return NextResponse.json({ error: tracksError?.message || albumsError?.message }, { status: 400 });
    }

    return NextResponse.json({
        tracks: tracks || [],
        albumPacks: albumPacks || []
    });
}
