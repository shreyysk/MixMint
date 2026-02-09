import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabaseServer";
import { DJService } from "@/server/services/DJService";

export async function POST(req: Request) {
    try {
        const authHeader = req.headers.get("authorization");
        if (!authHeader) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

        const token = authHeader.replace("Bearer ", "");
        const { data: { user }, error: authError } = await supabaseServer.auth.getUser(token);

        if (authError || !user) return NextResponse.json({ error: "Invalid session" }, { status: 401 });

        const result = await DJService.activate(user.id, user.email);

        return NextResponse.json(result);
    } catch (err: any) {
        console.error("[ACTIVATE_ERROR]:", err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
