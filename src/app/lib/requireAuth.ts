import { supabaseServer } from "@/app/lib/supabaseServer";

export async function requireAuth() {
    const {
        data: { user },
        error,
    } = await supabaseServer.auth.getUser();

    if (!user || error) {
        throw new Error("UNAUTHORIZED");
    }

    return user;
}
