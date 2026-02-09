import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabaseServer";
import { TrackService } from "@/server/services/TrackService";

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

    const result = await TrackService.getByDjId(dj.id);

    return NextResponse.json(result);
}
