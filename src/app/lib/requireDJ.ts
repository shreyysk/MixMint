import { supabaseServer } from "@/app/lib/supabaseServer";

export async function requireDJ(userId: string) {
    const { data } = await supabaseServer
        .from("profiles")
        .select("role")
        .eq("id", userId)
        .single();

    if (!data || data.role !== "dj") {
        throw new Error("FORBIDDEN");
    }
}
