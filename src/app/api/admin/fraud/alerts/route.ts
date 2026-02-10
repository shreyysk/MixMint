import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/admin/fraud/alerts
 * Returns fraud alerts for admin review
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();

    // Check admin role
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    const { searchParams } = new URL(req.url);
    const status = searchParams.get("status") || "pending";
    const severity = searchParams.get("severity");

    let query = supabaseServer
      .from("fraud_alerts")
      .select(`
        *,
        profiles (full_name, email)
      `)
      .eq("status", status)
      .order("created_at", { ascending: false })
      .limit(50);

    if (severity) {
      query = query.eq("severity", severity);
    }

    const { data: alerts, error } = await query;

    if (error) throw error;

    return ok({ alerts });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}

/**
 * PATCH /api/admin/fraud/alerts
 * Update fraud alert status
 */
export async function PATCH(req: Request) {
  try {
    const user = await requireAuth();

    // Check admin role
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    const { alertId, status, adminNotes } = await req.json();

    if (!alertId || !status) {
      return fail("Alert ID and status required", 400);
    }

    const { error } = await supabaseServer
      .from("fraud_alerts")
      .update({
        status,
        reviewed_by: user.id,
        reviewed_at: new Date().toISOString(),
        details: adminNotes ? { admin_notes: adminNotes } : undefined
      })
      .eq("id", alertId);

    if (error) throw error;

    return ok({ success: true });
  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
