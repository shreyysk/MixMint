import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

export async function GET() {
    try {
        const user = await requireAuth();

        // Get balance
        const { data: balance } = await supabaseServer
            .from('points')
            .select('balance')
            .eq('id', user.id)
            .single();

        // Get history
        const { data: history } = await supabaseServer
            .from('points_history')
            .select('*')
            .eq('profile_id', user.id)
            .order('created_at', { ascending: false })
            .limit(50);

        return ok({
            balance: balance?.balance || 0,
            totalEarned: balance?.balance || 0, // Simplified for now
            history: history || []
        });
    } catch (err: any) {
        console.error("[POINTS_API_ERROR]:", err);
        return fail(err.message || "Internal error", 500);
    }
}
