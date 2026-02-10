import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { requireDJ } from "@/lib/requireDJ";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/dj/analytics
 * Fetches advanced sale analytics for the logged-in DJ.
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();
    await requireDJ(user.id);

    const { searchParams } = new URL(req.url);
    const days = Number(searchParams.get("days")) || 30;

    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // 1. Fetch aggregate metrics from the view
    const { data: analytics, error: analyticsError } = await supabaseServer
      .from("dj_sale_analytics")
      .select("*")
      .eq("dj_id", user.id)
      .gte("sale_date", startDate.toISOString());

    if (analyticsError) throw analyticsError;

    // 2. Fetch Geography breakdown
    const geoBreakdown = (analytics || []).reduce((acc: any, curr: any) => {
      const country = curr.country || "Unknown";
      acc[country] = (acc[country] || 0) + curr.total_sales;
      return acc;
    }, {});

    // 3. Fetch Recent Sales with IP details
    const { data: recentSales } = await supabaseServer
      .from("purchases")
      .select("id, content_type, price_paid, created_at, location_data")
      .eq("seller_id", user.id)
      .order("created_at", { ascending: false })
      .limit(10);

    return ok({
      summary: analytics,
      geoBreakdown,
      recentSales,
      timeframe: { days, startDate: startDate.toISOString() }
    });

  } catch (err: any) {
    console.error("[DJ_ANALYTICS_API_ERROR]:", err);
    return fail(err.message || "Internal error", 500);
  }
}
