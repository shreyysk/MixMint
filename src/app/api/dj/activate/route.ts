import { NextResponse } from "next/server";
import { supabaseServer } from "@/app/lib/supabaseServer";

export async function POST(req: Request) {
    try {
        const authHeader = req.headers.get("authorization");
        if (!authHeader) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

        const token = authHeader.replace("Bearer ", "");
        const { data: { user }, error: authError } = await supabaseServer.auth.getUser(token);

        if (authError || !user) return NextResponse.json({ error: "Invalid session" }, { status: 401 });

        // 1. Force update the core profile to 'dj' using server-side client
        const { error: profileError } = await supabaseServer
            .from("profiles")
            .upsert({ id: user.id, role: "dj" });

        if (profileError) throw profileError;

        // 2. Ensure DJ profile is created and approved
        const { data: existing } = await supabaseServer
            .from("dj_profiles")
            .select("id")
            .eq("user_id", user.id)
            .single();

        if (existing) {
            const { error: updateError } = await supabaseServer
                .from("dj_profiles")
                .update({ status: "approved" })
                .eq("user_id", user.id);
            if (updateError) throw updateError;
        } else {
            const { error: insertError } = await supabaseServer
                .from("dj_profiles")
                .insert({
                    user_id: user.id,
                    dj_name: user.email?.split("@")[0] || "New DJ",
                    slug: `dj-${user.id.slice(0, 8)}`,
                    status: "approved",
                    bio: "Activated via fix-role utility",
                });
            if (insertError) throw insertError;
        }

        return NextResponse.json({ success: true, message: "DJ Account Fully Activated" });
    } catch (err: any) {
        console.error("[ACTIVATE_ERROR]:", err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
