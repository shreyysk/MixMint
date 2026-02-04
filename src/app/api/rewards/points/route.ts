import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { ok, fail } from "@/app/lib/apiResponse";

export async function GET() {
    try {
        const user = await requireAuth();

        // Get balance
        const { data: balance } = await supabaseServer
            .from('user_points')
            .select('balance, total_earned')
            .eq('profile_id', user.id)
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
            totalEarned: balance?.total_earned || 0,
            history: history || []
        });
    } catch (err: any) {
        console.error("[POINTS_API_ERROR]:", err);
        return fail(err.message || "Internal error", 500);
    }
}
